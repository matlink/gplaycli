#!/usr/bin/python


from google.protobuf import descriptor
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from google.protobuf import text_format
from google.protobuf.message import Message
from Crypto.Util import asn1
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from Crypto.Cipher import PKCS1_OAEP

import requests
import base64
import struct
import itertools

from . import googleplay_pb2, config, utils

ssl_verify = True


class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RequestError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class GooglePlayAPI(object):
    """Google Play Unofficial API Class

    Usual APIs methods are login(), search(), details(), bulkDetails(),
    download(), browse(), reviews() and list()."""

    BASE = "https://android.clients.google.com/"
    FDFE = BASE + "fdfe/"
    UPLOADURL = FDFE + "uploadDeviceConfig"
    SEARCHURL = FDFE + "search"
    CHECKINURL = BASE + "checkin"
    AUTHURL = BASE + "auth"

    ACCOUNT = "HOSTED_OR_GOOGLE"
    authSubToken = None
    gsfId = None

    def __init__(self, debug=False):
        # you must use a device-associated androidId value
        self.preFetch = {}
        self.lang = config.LANG
        self.debug = debug

    def encrypt_password(self, login, passwd):
        """Encrypt the password using the google publickey, using
        the RSA encryption algorithm"""

        binaryKey = base64.b64decode(config.GOOGLE_PUBKEY)
        i = utils.readInt(binaryKey, 0)
        modulus = utils.toBigInt(binaryKey[4:][0:i])
        j = utils.readInt(binaryKey, i+4)
        exponent = utils.toBigInt(binaryKey[i+8:][0:j])

        seq = asn1.DerSequence()
        seq.append(modulus)
        seq.append(exponent)

        publicKey = RSA.importKey(seq.encode())
        cipher = PKCS1_OAEP.new(publicKey)
        combined = login.encode() + b'\x00' + passwd.encode()
        encrypted = cipher.encrypt(combined)
        h = b'\x00' + SHA.new(binaryKey).digest()[0:4]
        return base64.urlsafe_b64encode(h + encrypted)

    def _try_register_preFetch(self, protoObj):
        fields = [i.name for (i, _) in protoObj.ListFields()]
        if ("preFetch" in fields):
            for p in protoObj.preFetch:
                self.preFetch[p.url] = p.response

    def setAuthSubToken(self, authSubToken):
        self.authSubToken = authSubToken

        # put your auth token in config.py to avoid multiple login requests
        if self.debug:
            print("authSubToken: " + authSubToken)

    def getDefaultHeaders(self):
        """Return the default set of request headers, which
        can later be updated, based on the request type"""

        headers = {
            "Accept-Language": "en-US",
            "X-DFE-Encoded-Targets":
                "CAEScFfqlIEG6gUYogFWrAISK1WDAg+hAZoCDgIU1gYEOIACFkLMAeQBnASLATlASUuyAyqCAjY5igOMBQzfA/IClwFbApUC4ANbtgKVAS7OAX8YswHFBhgDwAOPAmGEBt4OfKkB5weSB5AFASkiN68akgMaxAMSAQEBA9kBO7UBFE1KVwIDBGs3go6BBgEBAgMECQgJAQIEAQMEAQMBBQEBBAUEFQYCBgUEAwMBDwIBAgOrARwBEwMEAg0mrwESfTEcAQEKG4EBMxghChMBDwYGASI3hAEODEwXCVh/EREZA4sBYwEdFAgIIwkQcGQRDzQ2fTC2AjfVAQIBAYoBGRg2FhYFBwEqNzACJShzFFblAo0CFxpFNBzaAd0DHjIRI4sBJZcBPdwBCQGhAUd2A7kBLBVPngEECHl0UEUMtQETigHMAgUFCc0BBUUlTywdHDgBiAJ+vgKhAU0uAcYCAWQ/"
                "5ALUAw1UwQHUBpIBCdQDhgL4AY4CBQICjARbGFBGWzA1CAEMOQH+BRAOCAZywAIDyQZ2MgM3BxsoAgUEBwcHFia3AgcGTBwHBYwBAlcBggFxSGgIrAEEBw4QEqUCASsWadsHCgUCBQMD7QICA3tXCUw7ugJZAwGyAUwpIwM5AwkDBQMJA5sBCw8BNxBVVBwVKhebARkBAwsQEAgEAhESAgQJEBCZATMdzgEBBwG8AQQYKSMUkAEDAwY/CTs4/wEaAUt1AwEDAQUBAgIEAwYEDx1dB2wGeBFgTQ",
            "User-Agent": "Android-Finsky/7.1.15 (api=3,versionCode=80798000,sdk=23,device=angler,hardware=angler,product=angler)",
        }
        if self.gsfId is not None:
            headers["X-DFE-Device-Id"] = "{0:x}".format(self.gsfId)
        if self.authSubToken is not None:
            headers["Authorization"] = "GoogleLogin auth=%s" % self.authSubToken
        return headers

    def checkin(self, email, ac2dmToken):
        headers = self.getDefaultHeaders()
        headers["Content-Type"] = "application/x-protobuffer"

        request = config.getAndroidCheckinRequest()

        stringRequest = request.SerializeToString()
        res = requests.post(self.CHECKINURL, data=stringRequest,
                            headers=headers, verify=ssl_verify)
        response = googleplay_pb2.AndroidCheckinResponse()
        response.ParseFromString(res.content)

        securityToken = "{0:x}".format(response.securityToken)

        # checkin again to upload gfsid
        request2 = googleplay_pb2.AndroidCheckinRequest()
        request2.CopyFrom(request)
        request2.id = response.androidId
        request2.securityToken = response.securityToken
        request2.accountCookie.append("[" + email + "]")
        request2.accountCookie.append(ac2dmToken)
        stringRequest = request2.SerializeToString()
        res2 = requests.post(self.CHECKINURL, data=stringRequest,
                             headers=headers, verify=ssl_verify)

        return response.androidId

    def uploadDeviceConfig(self):
        """Upload the device configuration defined in the file
        *device.properties* to the google account. Default device is a Google Nexus 6P"""

        upload = googleplay_pb2.UploadDeviceConfigRequest()
        upload.deviceConfiguration.CopyFrom(config.getDeviceConfig())
        headers = self.getDefaultHeaders()
        headers["X-DFE-Enabled-Experiments"] = "cl:billing.select_add_instrument_by_default"
        headers["X-DFE-Unsupported-Experiments"] = "nocache:billing.use_charging_poller,market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes"
        headers["X-DFE-Client-Id"] = "am-android-google"
        headers["X-DFE-SmallestScreenWidthDp"] = "320"
        headers["X-DFE-Filter-Level"] = "3"
        stringRequest = upload.SerializeToString()
        res = requests.post(self.UPLOADURL, data=stringRequest,
                            headers=headers, verify=ssl_verify)
        response = googleplay_pb2.ResponseWrapper.FromString(res.content)


    def login(self, email=None, password=None, gsfId=None, authSubToken=None):
        """Login to your Google Account.
        For first time login you should provide:
            * email
            * password
        For the following logins you need to provide:
            * gsfId
            * authSubToken"""
        if email is not None and password is not None:
            # First time setup, where we obtain an ac2dm token and
            # upload device information

            encryptedPass = self.encrypt_password(email, password).decode('utf-8')
            # AC2DM token
            params = {
                "Email": email,
                "EncryptedPasswd": encryptedPass,
                "service": "ac2dm",
                "add_account": "1",
                "accountType": self.ACCOUNT,
                "has_permission": "1",
                "app": "com.google.android.gsf",
                "source": "android",
                "device_country": "en",
                "lang": self.lang,
                "sdk_version": "25",
                "client_sig": "38918a453d07199354f8b19af05ec6562ced5788"
            }
            response = requests.post(self.AUTHURL, data=params, verify=ssl_verify)
            data = response.text.split()
            params = {}
            for d in data:
                if "=" not in d:
                    continue
                k, v = d.split("=")[0:2]
                params[k.strip().lower()] = v.strip()
            if "auth" in params:
                ac2dmToken = params["auth"]
            elif "error" in params:
                raise LoginError("server says: " + params["error"])
            else:
                raise LoginError("Auth token not found.")

            self.gsfId = self.checkin(email, ac2dmToken)
            if self.debug:
                print("Google Services Framework Id: %s" % "{0:x}".format(self.gsfId))
            self.getAuthSubToken(email, encryptedPass)
            if self.debug:
                print("Uploading device configuration")
            self.uploadDeviceConfig()
        elif gsfId is not None and authSubToken is not None:
            # no need to initialize API
            self.gsfId = gsfId
            self.setAuthSubToken(authSubToken)
            # check if token is valid with a simple search
            self.search('firefox', 1, None)
        else:
            raise LoginError('Either (email,pass) or (gsfId, authSubToken) is needed')

    def getAuthSubToken(self, email, passwd):
        params = {
            "Email": email,
            "EncryptedPasswd": passwd,
            "accountType": self.ACCOUNT,
            "has_permission": "1",
            "source": "android",
            "device_country": "en",
            "service": "androidmarket",
            "app": "com.android.vending",
            "lang": self.lang,
            "sdk_version": "25",
            "client_sig": "38918a453d07199354f8b19af05ec6562ced5788"
        }
        response = requests.post(self.AUTHURL, data=params, verify=ssl_verify)
        data = response.text.split()
        params = {}
        for d in data:
            if "=" not in d:
                continue
            k, v = d.split("=")[0:2]
            params[k.strip().lower()] = v.strip()
        if "auth" in params:
            self.setAuthSubToken(params["auth"])
        elif "error" in params:
            raise LoginError("server says: " + params["error"])
        else:
            raise LoginError("Auth token not found.")

    def executeRequestApi2(self, path, datapost=None,
                           post_content_type="application/x-www-form-urlencoded; charset=UTF-8"):
        if self.authSubToken == None:
            raise Exception("You need to login before executing any request")
        if (datapost is None and path in self.preFetch):
            data = self.preFetch[path]
        else:
            headers = self.getDefaultHeaders()

            if datapost is not None:
                headers["Content-Type"] = post_content_type

            url = self.FDFE + path
            if datapost is not None:
                response = requests.post(url, data=str(datapost),
                                         headers=headers, verify=ssl_verify)
            else:
                response = requests.get(url, headers=headers,
                                        verify=ssl_verify)
            data = response.content

        message = googleplay_pb2.ResponseWrapper.FromString(data)
        if message.commands.displayErrorMessage != "":
            raise RequestError(message.commands.displayErrorMessage)
        self._try_register_preFetch(message)

        return message

    def search(self, query, nb_result, offset=None):
        if self.authSubToken == None:
            raise Exception("You need to login before executing any request")
        path = "search?c=3&q=%s" % requests.utils.quote(query)

        if (offset is not None):
            path += "&o=%d" % int(offset)

        data = self.executeRequestApi2(path)
        # TODO: can response contain more than 1 cluster?
        cluster = data.preFetch[0].response.payload.listResponse.cluster[0]
        # cluster has more than 1 doc usually, and each doc has some
        # childs representing the applications. So we chain together every child
        # of every doc
        apps = itertools.chain.from_iterable([doc.child for doc in cluster.doc])
        output = list(map(utils.fromDocToDictionary, apps))
        return output

    def details(self, packageName):
        """Get app details from a package name.
        packageName is the app unique ID (usually starting with 'com.')."""
        path = "details?doc=%s" % requests.utils.quote(packageName)
        message = self.executeRequestApi2(path)
        return message.payload.detailsResponse

    def bulkDetails(self, packageNames):
        """Get several apps details from a list of package names.

        This is much more efficient than calling N times details() since it
        requires only one request.

        packageNames is a list of app ID (usually starting with 'com.')."""

        path = "bulkDetails"
        req = googleplay_pb2.BulkDetailsRequest()
        req.docid.extend(packageNames)
        data = req.SerializeToString()
        message = self.executeRequestApi2(path,
                                          data.decode("utf-8"),
                                          "application/x-protobuf")
        response = message.payload.bulkDetailsResponse
        detailsList = [entry.doc for entry in response.entry]
        result = list(map(utils.fromDocToDictionary, detailsList))
        return result

    def browse(self, cat=None, ctr=None):
        """Browse categories.
        cat (category ID) and ctr (subcategory ID) are used as filters."""
        path = "browse?c=3"
        if cat is not None:
            path += "&cat=%s" % requests.utils.quote(cat)
        if ctr is not None:
            path += "&ctr=%s" % requests.utils.quote(ctr)
        message = self.executeRequestApi2(path)
        return message.payload.browseResponse

    def list(self, cat, ctr=None, nb_results=None, offset=None):
        """List apps.

        If ctr (subcategory ID) is None, returns a list of valid subcategories.

        If ctr is provided, list apps within this subcategory."""
        path = "list?c=3&cat=%s" % requests.utils.quote(cat)
        if ctr is not None:
            path += "&ctr=%s" % requests.utils.quote(ctr)
        if nb_results is not None:
            path += "&n=%s" % requests.utils.quote(nb_results)
        if offset is not None:
            path += "&o=%s" % requests.utils.quote(offset)
        message = self.executeRequestApi2(path)
        return message.payload.listResponse

    def reviews(self, packageName, filterByDevice=False, sort=2,
                nb_results=None, offset=None):
        """Browse reviews.
        packageName is the app unique ID.
        If filterByDevice is True, return only reviews for your device."""
        path = "rev?doc=%s&sort=%d" % (requests.utils.quote(packageName), sort)
        if (nb_results is not None):
            path += "&n=%d" % int(nb_results)
        if (offset is not None):
            path += "&o=%d" % int(offset)
        if(filterByDevice):
            path += "&dfil=1"
        message = self.executeRequestApi2(path)
        return message.payload.reviewResponse

    def download(self, packageName, versionCode,
                 offerType=1, progress_bar=False):
        """Download an app and return its raw data (APK file).

        packageName is the app unique ID (usually starting with 'com.').

        versionCode can be grabbed by using the details() method on the given
        app."""

        if self.authSubToken == None:
            raise Exception("You need to login before executing any request")

        path = "purchase"
        headers = self.getDefaultHeaders()
        params = {
            'ot': str(offerType),
            'doc': packageName,
            'vc': str(versionCode)
        }
        url = self.FDFE + path
        response = requests.post(url, headers=headers,
                                 params=params, verify=ssl_verify)

        resObj = googleplay_pb2.ResponseWrapper.FromString(response.content)
        if resObj.commands.displayErrorMessage != "":
            raise RequestError(resObj.commands.displayErrorMessage)
        else:
            dlToken = resObj.payload.buyResponse.downloadToken
            path = "delivery"
            params['dtok'] = dlToken
            url = "https://android.clients.google.com/fdfe/%s" % path
            response = requests.get(url, headers=headers,
                                     params=params, verify=ssl_verify)
            resObj = googleplay_pb2.ResponseWrapper.FromString(response.content)
            downloadUrl = resObj.payload.deliveryResponse.appDeliveryData.downloadUrl
            cookie = resObj.payload.deliveryResponse.appDeliveryData.downloadAuthCookie[0]
            cookies = {
                str(cookie.name): str(cookie.value)
            }
            return requests.get(downloadUrl, headers=headers,
                                cookies=cookies, verify=ssl_verify).content

