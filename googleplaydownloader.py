#! /usr/bin/python2
# -*- coding: utf-8 -*-
"""
GooglePlayDownloader
Copyright (C) 2013   Tuxicoman

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import
import wx, platform, os, sys, thread, subprocess, urllib, json
import ConfigParser as configparser
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import wx.lib.hyperlink as hl
import webbrowser

HERE = os.path.abspath(os.path.dirname(__file__))
_icons_path = os.path.join(HERE, 'img')

from ext_libs.googleplay_api.googleplay import GooglePlayAPI #GooglePlayAPI
from ext_libs.googleplay_api.googleplay import LoginError
from ext_libs.androguard.core.bytecodes import apk as androguard_apk #Androguard


config = {}
dlg = None

def default_values(input_dict, contact_developper = True):
  config_dict = {}
  config_dict["download_folder_path"] = os.path.expanduser('~')
  config_dict["language"] = "fr_FR"
  config_dict["android_ID"] = ""
  config_dict["gmail_password"]= ""
  config_dict["gmail_address"] = ""

  if contact_developper == True:
    #Get default account credentials
    try:
      cfg_file = urllib.urlopen("http://jesuislibre.net/googleplaydownloader.cfg")
    except IOError, exc:
      return "Can't contact developper website to get default credentials.\n%s" % exc
    try:
      default_account_dict = json.loads(cfg_file.read())
    except ValueError, exc:
      return "Not valid default config file. Please contact developper.\n%s" % exc

    config_dict["android_ID"] = str(default_account_dict["android_ID"])
    config_dict["gmail_password"] = str(default_account_dict["gmail_password"])
    config_dict["gmail_address"] = str(default_account_dict["gmail_address"])

  input_dict.update(config_dict)

config_file_path = os.path.expanduser('~/.config/googleplaydownloader/googleplaydownloader.conf')
config_section = "googleplaydownloader"

def read_config(config_file_path, config_dict):
  config_parser = configparser.RawConfigParser()
  config_parser.read(config_file_path)
  for key, previous_value in config_dict.items():
    if config_parser.has_option(config_section, key):
      new_value = config_parser.get(config_section, key).decode('utf-8')
      if type(previous_value) in (list, bool):
        new_value = json.loads(new_value)
      config_dict[key] = new_value

def save_config(config_file_path, config_dict):
  config_parser = configparser.RawConfigParser()
  config_parser.add_section(config_section)
  for key, value in config_dict.items():
    if type(value) in (list, bool) :
      value = json.dumps(value)
    config_parser.set(config_section, key, value.encode('utf-8'))

  config_file_folder = os.path.dirname(config_file_path)
  if not os.path.exists(config_file_folder) :
    os.makedirs(config_file_folder)
  with open(config_file_path, 'w') as configfile:
    config_parser.write(configfile)

def sizeof_fmt(num):
  for x in ['bytes','KB','MB','GB','TB']:
    if num < 1024.0:
        return "%3.1f%s" % (num, x)
    num /= 1024.0

#List autoresize
class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
  def __init__(self, parent, ID, style):
    self.parent = parent
    wx.ListCtrl.__init__(self, parent, ID, style=style)
    ListCtrlAutoWidthMixin.__init__(self)

    self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

  def autoresize(self):
    for i in range(self.GetColumnCount()):
      #Autoresize column using header
      self.SetColumnWidth(i, wx.LIST_AUTOSIZE_USEHEADER)
      width1 = self.GetColumnWidth(i)

      #Autoresize column using content
      self.SetColumnWidth(i, wx.LIST_AUTOSIZE)
      width2 = self.GetColumnWidth(i)

      if width2 < width1:
        self.SetColumnWidth(i, wx.LIST_AUTOSIZE_USEHEADER)

  def fill_headers(self, headers):
    for i, header in enumerate(headers):
      self.InsertColumn(i, u"%s" % header)

  def OnItemActivated(self, event):
    selected_item = event.m_itemIndex
    packagename = self.data[self.GetItemData(selected_item)]
    view_webpage(packagename)


def analyse_local_apks(list_of_apks, playstore_api, download_folder_path, dlg, return_function):
  list_apks_to_update = []
  for position, filename in enumerate(list_of_apks):
    #wx.CallAfter(dlg.Update, position, "%i/%i : %s\nPlease Wait..." %(position+1, len(list_of_apks), filename))

    #Get APK info from file on disk
    filepath = os.path.join(download_folder_path, filename)
    a = androguard_apk.APK(filepath)
    apk_version_code = a.get_androidversion_code()
    packagename = a.get_package()

    #Get APK info from store
    m =playstore_api.details(packagename)
    doc = m.docV2
    store_version_code = doc.details.appDetails.versionCode

    #Compare
    if int(apk_version_code) != int(store_version_code) and int(store_version_code) != 0:
      #Add to the download list
      list_apks_to_update.append([packagename, filename, int(apk_version_code), int(store_version_code)])

  return_function(list_apks_to_update)
  # wx.CallAfter(dlg.Update, position+1)   #Reach end of progress dialog
  # wx.CallAfter(return_function, list_apks_to_update)


def download_selection(playstore_api, list_of_packages_to_download, dlg, return_function):
  failed_downloads = []
  for position, item in enumerate(list_of_packages_to_download):
    packagename, filename = item

    #Check for download folder
    download_folder_path = config["download_folder_path"]
    if not os.path.isdir(download_folder_path):
      os.mkdir(download_folder_path)

    # Get the version code and the offer type from the app details
    m = playstore_api.details(packagename)
    doc = m.docV2
    title = doc.title
    vc = doc.details.appDetails.versionCode

    #Update progress dialog
    # wx.CallAfter(dlg.Update, position, "%i/%i : %s\n%s\nSize : %s\nPlease Wait...(there is no download progression)" %(position+1, len(list_of_packages_to_download), title, packagename, sizeof_fmt(doc.details.appDetails.installationSize)))
    print "Downloading ..."
    # Download
    try:
      data = playstore_api.download(packagename, vc)
    except Exception as exc:
      print "Error while downloading %s : %s" % (packagename, exc)
      failed_downloads.append((item, exc))
    else:
      if filename == None:
        filename = packagename + ".apk"
      filepath = os.path.join(download_folder_path,filename)

      try:
        open(filepath, "wb").write(data)
      except IOError, exc:
        print "Error while writing %s : %s" % (packagename, exc)
        failed_downloads.append((item, exc))
  return_function(failed_downloads)
  # wx.CallAfter(dlg.Update, position+1)   #Reach end of progress dialog
  # wx.CallAfter(return_function,failed_downloads)


def softwareID(query) :
  if query == "name":
    return u"Google Play Downloader"
  if query == "version":
    with open(os.path.join(HERE, "version.txt"), "r") as f:
      version = f.read().strip()
    return version
  if query == "copyright":
    return u"Tuxicoman"

def view_webpage(packagename):
  language_code  = config["language"].split("_")[0]
  url = "https://play.google.com/store/apps/details?id=%s&hl=%s" % (packagename,language_code)
  webbrowser.open(url)

class MainPanel(object):
  def __init__(self):
    pass
    # wx.Panel.__init__(self, parent, -1)

    # #Search
    # search_title = wx.StaticText(self, -1, u"Search :")
    # search_entry = wx.SearchCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
    # search_entry.SetDescriptiveText(u"Search")
    # self.Bind(wx.EVT_TEXT_ENTER, lambda e: self.search(results_list, search_entry.GetValue(), nb_results=20), search_entry)

    # #Search Layout
    # searchbox = wx.BoxSizer(wx.VERTICAL)
    # searchbox.Add(search_title)
    # searchbox.Add(search_entry, -1, wx.EXPAND|wx.ADJUST_MINSIZE)

    # #Config
    # config_title = wx.StaticText(self, -1, u"Settings :")
    # config_button = wx.Button(self, -1, "Configure")
    # self.Bind(wx.EVT_BUTTON, lambda e: self.show_config(), config_button)

    # #Config layout
    # configbox = wx.BoxSizer(wx.VERTICAL)
    # configbox.Add(config_title)
    # configbox.Add(config_button)

    # #Results
    # results_title = wx.StaticText(self, -1, u"Results :")
    # results_list = AutoWidthListCtrl(self, -1, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
    # results_list.headers =[ "Title",
    #   "Creator",
    #   "Size",
    #   "Num Downloads",
    #   "Last update",
    #   "AppID",
    #   "Version Code",
    #   "Rating"
    #   ]

    # results_list.fill_headers(results_list.headers)
    # results_list.autoresize()

    # #Results Layout
    # resultsbox = wx.BoxSizer(wx.VERTICAL)
    # resultsbox.Add(results_title)
    # resultsbox.Add(results_list, 1, wx.EXPAND|wx.ADJUST_MINSIZE)

    # #Buttons
    # self.webpage_button = wx.Button(self, -1, "View APK(s) info on the web")
    # self.webpage_button.Disable()
    # self.Bind(wx.EVT_BUTTON, lambda e: self.view_webpage_selection(results_list), self.webpage_button)
    # self.download_button = wx.Button(self, -1, "Download selected APK(s)")
    # self.download_button.Disable()
    # self.Bind(wx.EVT_BUTTON, lambda e: self.prepare_download_selection(results_list), self.download_button)


    # #Buttons layout
    # buttonsbox = wx.BoxSizer(wx.HORIZONTAL)
    # buttonsbox.Add(self.webpage_button, 1, wx.ALIGN_LEFT|wx.TOP,  border=3)
    # buttonsbox.Add(self.download_button, 1, wx.ALIGN_LEFT|wx.TOP,  border=3)

    # #Update
    # #update_title = wx.StaticText(self, -1, u"Update :")
    # self.update_button = wx.Button(self, -1, "Search updates for local APK(s)")
    # self.Bind(wx.EVT_BUTTON, self.prepare_analyse_apks, self.update_button )

    # #Update layout
    # updatebox = wx.BoxSizer(wx.VERTICAL)
    # #updatebox.Add(update_title)
    # updatebox.Add(self.update_button, 0, wx.EXPAND|wx.TOP,  border=3)


    # #Credits
    # creditsbox = wx.BoxSizer(wx.HORIZONTAL)
    # creditsbox.AddMany([wx.StaticText(self, -1, u"Credits : "), hl.HyperLinkCtrl(self, wx.ID_ANY, u"Tuxicoman", URL="http://tuxicoman.jesuislibre.net"), wx.StaticText(self, -1, u" / GooglePlay unofficial API : "), hl.HyperLinkCtrl(self, wx.ID_ANY, u"Emilien Girault", URL="http://www.segmentationfault.fr"), wx.StaticText(self, -1, u" / AndroidID generation : "), hl.HyperLinkCtrl(self, wx.ID_ANY, u"Nicolas Viennot", URL="https://github.com/nviennot/android-checkin")])

    # #Layout
    # bigbox = wx.BoxSizer(wx.VERTICAL)
    # topbox = wx.BoxSizer(wx.HORIZONTAL)
    # topbox.Add(searchbox, 1, wx.EXPAND|wx.ADJUST_MINSIZE)
    # topbox.Add(configbox, 0, wx.EXPAND|wx.ADJUST_MINSIZE|wx.LEFT, border=5)
    # bigbox.Add(topbox, 0, wx.EXPAND|wx.ADJUST_MINSIZE)
    # bigbox.Add(resultsbox, 1, wx.EXPAND|wx.ADJUST_MINSIZE)
    # bigbox.Add(buttonsbox, 0, wx.EXPAND|wx.ADJUST_MINSIZE)
    # bigbox.Add(updatebox, 0, wx.EXPAND|wx.ADJUST_MINSIZE)
    # bigbox.Add(creditsbox, 0)


    # self.SetSizer(bigbox)
    # self.SetMinSize((700,400))
    # search_entry.SetFocus()


  def prepare_analyse_apks(self):
    #if self.ask_download_folder_path() == True:
    download_folder_path = config["download_folder_path"]
    list_of_apks = [filename for filename in os.listdir(download_folder_path) if os.path.splitext(filename)[1] == ".apk"]
    if len(list_of_apks) > 0:
      # dlg = wx.ProgressDialog("Updating APKs",
      #                            "_" * 30 + "\n"*2,
      #                            maximum = len(list_of_apks),
      #                            parent=self,
      #                            style = wx.PD_AUTO_HIDE
      #                            )
      print "Updating apks ..."
      analyse_local_apks(list_of_apks, self.playstore_api, download_folder_path, dlg, self.prepare_download_updates)




  def search(self, results_list, search_string, nb_results):
    #Query results
    results = self.playstore_api.search(search_string, nb_results=nb_results).doc
    if len(results) > 0:
      results = results[0].child
    #else : No results found !

    #Fill list in GUI
    results_list.ClearAll()
    results_list.data = []

    results_list.fill_headers(results_list.headers)

    i = 0
    for result in results:
      if result.offer[0].checkoutFlowRequired == False: #if Free to download
        l = [ result.title,
              result.creator,
              sizeof_fmt(result.details.appDetails.installationSize),
              result.details.appDetails.numDownloads,
              result.details.appDetails.uploadDate,
              result.docid,
              result.details.appDetails.versionCode,
              "%.2f" % result.aggregateRating.starRating
              ]

        item = results_list.InsertStringItem(i, "")
        for j, text in enumerate(l):
          results_list.SetStringItem(item,j,u"%s" % text)


        #Associate data
        results_list.data.append(result.docid)
        results_list.SetItemData(item, i)

        #select first item
        if i == 0:
          results_list.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
          results_list.EnsureVisible(item)

        i+=1


    results_list.autoresize()

    #Disable button if there is no result
    if results_list.GetFirstSelected() != -1:
      self.download_button.Enable()
      self.webpage_button.Enable()
    else:
      self.download_button.Disable()
      self.webpage_button.Enable()

  def show_config(self):
    #Popup Config dialog
    dlg = ConfigDialog(self)
    dlg.CenterOnScreen()

    val = dlg.ShowModal()

    if val == wx.ID_OK:
      #Get data
      config["language"] = dlg.language.GetValue()
      config["android_ID"] = dlg.android_ID.GetValue()
      config["gmail_address"] = dlg.gmail_address.GetValue()
      config["gmail_password"] = dlg.gmail_password.GetValue()


    dlg.Destroy()

    save_config(config_file_path, config)

    #Connect to GooglePlay
    self.connect_to_googleplay_api()



  def view_webpage_selection(self, results_list):
    #Get list of packages selected
    list_of_packages = []
    selected_item = results_list.GetFirstSelected()
    while selected_item != -1 :
      packagename = results_list.data[results_list.GetItemData(selected_item)]
      list_of_packages.append(packagename)
      selected_item = results_list.GetNextSelected(selected_item)
    for packagename in list_of_packages:
      view_webpage(packagename)

  def after_download(self, failed_downloads):
    #Info message
    if len(failed_downloads) == 0 :
      message = "Download complete"
    else:
      message = "A few packages could not be downloaded :"
      for item, exception in failed_downloads:
        package_name, filename = item
        if filename !=None :
          message += "\n%s : %s" % (filename, package_name)
        else:
          message += "\n%s" % package_name
        message += "\n%s\n" % exception

    #Show info dialog
    # dlg = wx.MessageDialog(self, message,'Download report', wx.OK | wx.ICON_INFORMATION)
    # dlg.ShowModal()
    # dlg.Destroy()

  def ask_download_folder_path(self):
    dlg = wx.DirDialog(self, "Choose a download folder:",  defaultPath = config["download_folder_path"], style=wx.DD_DEFAULT_STYLE)
    return_value = dlg.ShowModal()
    dlg.Destroy()
    if return_value == wx.ID_OK :
      config["download_folder_path"] = dlg.GetPath()
      save_config(config_file_path, config)
      return True
    else:
      return False

  def connect_to_googleplay_api(self):
    AUTH_TOKEN = None

    api = GooglePlayAPI(androidId=config["android_ID"], lang=config["language"])
    try :
      api.login(config["gmail_address"], config["gmail_password"], AUTH_TOKEN)
    except LoginError, exc:
      print exc.value
      # dlg = wx.MessageDialog(self, "%s.\nUsing default credentials may solve the issue" % exc.value,'Connection to Play store failed', wx.OK | wx.ICON_INFORMATION)
      # dlg.ShowModal()
      # dlg.Destroy()
      success = False
    else:
      self.playstore_api = api
      success = True

    return success

  def prepare_download_selection(self, results_list):
    #Get list of packages selected
    list_of_packages_to_download = []
    selected_item = results_list.GetFirstSelected()
    while selected_item != -1 :
      packagename = results_list.data[results_list.GetItemData(selected_item)]
      list_of_packages_to_download.append([packagename, None])
      selected_item = results_list.GetNextSelected(selected_item)

    if len(list_of_packages_to_download) > 0:
      if self.ask_download_folder_path() == True:
        dlg = wx.ProgressDialog("Downloading APKs",
                                 " " * 30 + "\n"*4,
                                 maximum = len(list_of_packages_to_download),
                                 parent=self,
                                 style = wx.PD_CAN_ABORT| wx.PD_AUTO_HIDE
                                 )
        thread.start_new_thread(download_selection, (self.playstore_api, list_of_packages_to_download, dlg, self.after_download))


  def prepare_download_updates(self, list_apks_to_update):

    if len(list_apks_to_update) > 0:
      list_of_packages_to_download = []

      #Ask confirmation before downloading
      message = u"The following applications will be updated :"
      for packagename, filename, apk_version_code, store_version_code in list_apks_to_update :
        message += u"\n%s Version : %s -> %s" % (filename ,apk_version_code, store_version_code)
        list_of_packages_to_download.append([packagename, filename])
      message += "\n\nDo you agree?"
      print message 
      return_value = raw_input('y/n ?')
      # dlg = wx.MessageDialog(self, message, 'Updating APKs', wx.ICON_INFORMATION|wx.YES_NO )
      # return_value = dlg.ShowModal()
      # dlg.Destroy()

      if return_value == 'y':
        #Progress Dialog
        # dlg = wx.ProgressDialog("Updating APKs",
        #                          " " * 30 + "\n"*4,
        #                          maximum = len(list_of_packages_to_download),
        #                          parent=self,
        #                          style = wx.PD_CAN_ABORT|wx.PD_AUTO_HIDE
        #                          )
        print "Downloading ..."
        download_selection(self.playstore_api, list_of_packages_to_download, dlg, self.after_download)

class ConfigDialog(object):
  def __init__(self):
    pass
    # wx.Dialog.__init__(self, parent=parent, title="Configure Settings")

    # text_size = 250
    # self.sizer = sizer = wx.BoxSizer(wx.VERTICAL)
    # self.use_default_btn = wx.RadioButton(self, -1, "Default values")
    # self.Bind(wx.EVT_RADIOBUTTON, self.use_default_values, self.use_default_btn)
    # self.use_custom_btn = wx.RadioButton(self, -1, "Custom values")
    # self.Bind(wx.EVT_RADIOBUTTON, self.use_custom_values, self.use_custom_btn)
    # sizer.Add(self.use_default_btn, 0, wx.ALL, 5)
    # sizer.Add(self.use_custom_btn, 0, wx.ALL, 5)

    # self.gridSizer = gridSizer = wx.FlexGridSizer(rows=5, cols=2, hgap=5, vgap=5)
    # sizer.Add(self.gridSizer, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

    # self.custom_widgets = []

    # label = wx.StaticText(self, -1, "Gmail address:")
    # self.custom_widgets.append(label)
    # self.gmail_address = wx.TextCtrl(self, -1, "", size=(text_size,-1))
    # self.custom_widgets.append(self.gmail_address)
    # gridSizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT,5)
    # gridSizer.Add(self.gmail_address,1, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

    # label = wx.StaticText(self, -1, "Gmail password:")
    # self.custom_widgets.append(label)
    # self.gmail_password = wx.TextCtrl(self, -1, "", size=(text_size,-1))
    # self.custom_widgets.append(self.gmail_password)
    # gridSizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT,5)
    # gridSizer.Add(self.gmail_password,1, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

    # label = wx.StaticText(self, -1, "Android ID:")
    # self.custom_widgets.append(label)
    # self.android_ID = wx.TextCtrl(self, -1, "", size=(text_size,-1))
    # self.custom_widgets.append(self.android_ID)
    # gridSizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT,5)
    # gridSizer.Add(self.android_ID,1, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

    # label = wx.StaticText(self, -1, "")
    # gridSizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT,5)

    # android_id_btn = wx.Button(self, -1, "Generate new Android ID(requires Java installed)")
    # self.custom_widgets.append(android_id_btn)
    # self.Bind(wx.EVT_BUTTON, self.generate_android_id, android_id_btn)
    # gridSizer.Add(android_id_btn,0, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

    # label = wx.StaticText(self, -1, "Language:")
    # self.custom_widgets.append(label)
    # self.language = wx.TextCtrl(self, -1, "", size=(text_size,-1))
    # self.custom_widgets.append(self.language)
    # gridSizer.Add(label,0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT,5)
    # gridSizer.Add(self.language,1, wx.EXPAND|wx.ALIGN_CENTRE|wx.ALL, 5)

    # line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
    # sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)

    # btnsizer = wx.StdDialogButtonSizer()
    # btn = wx.Button(self, wx.ID_OK)
    # btn.SetDefault()
    # btnsizer.AddButton(btn)
    # btnsizer.Realize()
    # sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

    # self.SetSizer(sizer)
    # self.use_custom_values()
    # self.sizer.Fit(self)

  def use_default_values(self, event=None):
    # self.use_default_btn.SetValue(True)
    #Reset to default values
    # error = default_values(config)
    # if error != None :
    #   pass
      # dlg = wx.MessageDialog(self, "%s" % error,'Retrieval of default account failed', wx.OK | wx.ICON_INFORMATION)
      # dlg.ShowModal()
      # dlg.Destroy()
    self.fill_data()

    # for widget in self.custom_widgets:
    #   widget.Disable()

  def use_custom_values(self, event=None):
    self.use_custom_btn.SetValue(True)
    self.fill_data()

    for widget in self.custom_widgets:
      widget.Enable()

  def fill_data(self):
    #Fill data
    print config
    self.language.SetValue(config["language"])
    self.android_ID.SetValue(config["android_ID"])
    self.gmail_address.SetValue(config["gmail_address"])
    self.gmail_password.SetValue(config["gmail_password"])

  def generate_android_id(self, event=None):
    #Launch Java to create an AndroidID
    command = ["java","-jar", os.path.join(HERE,"ext_libs/android-checkin/target/android-checkin-1.1-jar-with-dependencies.jar"), "%s" % config["gmail_address"], "%s" % config["gmail_password"]]
    p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
    r = p.stderr.readlines()
    androidid_pattern = "AndroidId: "
    if len(r) > 9 and r[-1].find(androidid_pattern) != -1 and r[-1].find("\n") != -1:
      android_id = r[-1][len(androidid_pattern):r[-1].find("\n")]
      message = "sucessful"
    else:
      #Autogeneration of AndroidID failed
      message = "failed"
      print " ".join(command)
      print r
    dlg = wx.MessageDialog(self, "Autogeneration of AndroidID %s" % message,'Autogeneration of AndroidID %s' % message, wx.OK | wx.ICON_INFORMATION)
    dlg.ShowModal()
    dlg.Destroy()
    if message == "sucessful":
      self.android_ID.SetValue(android_id)



class MainFrame(wx.Frame):

  def __init__(self, parent, title):
    wx.Frame.__init__(self, None, -1, title, pos=wx.DefaultPosition, style=wx.DEFAULT_FRAME_STYLE)
    #self.SetDoubleBuffered(True) #This seems to eat CPU on Windows :-(
    self.application = parent
    self.panel = MainPanel(self)

    #Layout
    self.sizer = wx.BoxSizer(wx.VERTICAL)
    self.sizer.Add(self.panel, 1, wx.EXPAND|wx.ALL,  border=10)
    self.SetSizer(self.sizer)
    self.Fit()
    self.CenterOnScreen()

    ##Init

    #default config
    if os.path.isfile(config_file_path):
      error = default_values(config, contact_developper=False)
      #Reload config form file if any
      read_config(config_file_path, config)
    else:
      error = default_values(config)
      if error != None:
        dlg = wx.MessageDialog(self, "%s" % error,'Retrieval of default account failed', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()



    #Connection
    self.panel.connect_to_googleplay_api()

class App(wx.App):
  def OnInit(self):
    title=u"%s %s" % (softwareID("name"), softwareID("version"))
    self.SetAppName(softwareID("name"))
    fen = MainFrame(self, title)
    fen.SetIcon(wx.Icon(os.path.join(_icons_path,"icon.ico"), wx.BITMAP_TYPE_ICO))
    fen.SetMinSize(fen.GetSize())
    fen.Show(True)
    self.SetTopWindow(fen)
    return True


def main():
  if platform.system() == 'Linux' :
    app = App()
  else :
    app = App(redirect=False)
  if platform.system() == 'Windows' :
    try :
      import win32event
      mutex = win32event.CreateMutex(None, 1, libutils.softwareID("name"))
    except : pass

  #Launch GUI
  app.MainLoop()

if __name__ == '__main__':
  # main()
  pan = MainPanel()
  default_values(config)
  config["download_folder_path"] = sys.argv[1]
  pan.connect_to_googleplay_api()
  pan.prepare_analyse_apks()