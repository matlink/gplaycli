import struct
import sys

VERSION = sys.version_info[0]

def fromDocToDictionary(app):
    return {
        "docId": app.docid,
        "title": app.title,
        "author": app.creator,
        "offer": [{
            "micros": o.micros,
            "currencyCode": o.currencyCode,
            "formattedAmount": o.formattedAmount,
            "checkoutFlowRequired": o.checkoutFlowRequired,
            "offerType": o.offerType
        } for o in app.offer],
        "images": [{
            "imageType": img.imageType,
            "width": img.dimension.width if hasattr(img.dimension, "width")
                                         else 0,
            "height": img.dimension.height if hasattr(img.dimension, "height")
                                           else 0,
            "url": img.imageUrl,
            "supportsFifeUrlOptions": img.supportsFifeUrlOptions
        } for img in app.image],
        "versionCode": app.details.appDetails.versionCode,
        "installationSize": app.details.appDetails.installationSize,
        "numDownloads": app.details.appDetails.numDownloads,
        "uploadDate": app.details.appDetails.uploadDate,
        "files": [{
            "fileType": f.fileType,
            "version": f.versionCode,
            "size": f.size
        } for f in app.details.appDetails.file],
        "unstable": app.details.appDetails.unstable,
        "containsAds": app.details.appDetails.containsAds,
        "aggregateRating": {
            "type": app.aggregateRating.type,
            "starRating": app.aggregateRating.starRating,
            "ratingsCount": app.aggregateRating.ratingsCount,
            "oneStarRatings": app.aggregateRating.oneStarRatings,
            "twoStarRatings": app.aggregateRating.twoStarRatings,
            "threeStarRatings": app.aggregateRating.threeStarRatings,
            "fourStarRatings": app.aggregateRating.fourStarRatings,
            "fiveStarRatings": app.aggregateRating.fiveStarRatings,
            "commentCount": app.aggregateRating.commentCount
        },
        "dependencies": [{
            "packageName": d.packageName,
            "version": d.version
        } for d in app.details.appDetails.dependencies.dependency],
        "category": {
            "appType": app.relatedLinks.categoryInfo.appType,
            "appCategory": app.relatedLinks.categoryInfo.appCategory
        },
        "detailsUrl": app.detailsUrl
    }

def readInt(byteArray, start):
    """Read the byte array, starting from *start* position,
    as an 32-bit unsigned integer"""
    return struct.unpack("!L", byteArray[start:][0:4])[0]


def toBigInt(byteArray):
    """Convert the byte array to a BigInteger"""
    array = byteArray[::-1] # reverse array
    out = 0
    for key, value in enumerate(array):
        if VERSION == 3:
            decoded = struct.unpack("B", bytes([value]))[0]
        else:
            decoded = struct.unpack("B", value)[0]
        out = out | decoded << key*8
    return out
