import json
import platform
import sys
import time
from os.path import exists
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QFrame, QDialog, QListWidgetItem, QSplashScreen
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QPixmap
from onvif import ONVIFCamera
import vlc

from ui.mainwindow import Ui_MainWindow
from ui.managewindow import Ui_ManageWindow
from ui.addtemplatedialog import Ui_AddTemplateDialog
from ui.addstandsdialog import Ui_AddStandsDialog


class AddStandsDialog(QDialog):
    def __init__(self, parent):
        super(AddStandsDialog, self).__init__()
        self.ui = Ui_AddStandsDialog()
        self.ui.setupUi(self)
        self.parent = parent
        self.ui.stands_te.textChanged.connect(self.check_fill)
        self.ui.template_cb.currentTextChanged.connect(self.check_fill)
        self.ui.add_btn.clicked.connect(self.add)
        self.ui.cancel_btn.clicked.connect(self.cancel)
        self.update_templates()

    @pyqtSlot()
    def update_templates(self):
        self.ui.template_cb.clear()
        self.ui.template_cb.addItems(self.parent.parent.templates.keys())

    @pyqtSlot()
    def check_fill(self):
        if self.ui.stands_te.toPlainText() != '' and self.ui.template_cb:
            self.ui.add_btn.setEnabled(True)
        else:
            self.ui.add_btn.setEnabled(False)

    @pyqtSlot()
    def cancel(self):
        self.ui.stands_te.clear()
        self.hide()

    @pyqtSlot()
    def add(self):
        if self.ui.stands_te.toPlainText() != '':
            stands = {}
            for stand in self.ui.stands_te.toPlainText().splitlines():
                stands[stand.split(':')[0]] = {'template': self.ui.template_cb.currentText(), 'ip': stand.split(':')[1]}
            self.parent.parent.add_stands(stands)
            self.cancel()
            self.parent.update_stands_list()


class AddTemplateDialog(QDialog):
    def __init__(self, parent):
        super(AddTemplateDialog, self).__init__()
        self.parent = parent
        self.ui = Ui_AddTemplateDialog()
        self.ui.setupUi(self)
        self.ui.name_le.textChanged.connect(self.check_fill)
        self.ui.port_le.textChanged.connect(self.check_fill)
        self.ui.username_le.textChanged.connect(self.check_fill)
        self.ui.password_le.textChanged.connect(self.check_fill)
        self.ui.cancel_btn.clicked.connect(self.cancel)
        self.ui.add_btn.clicked.connect(self.add)

    @pyqtSlot()
    def check_fill(self):
        if self.ui.name_le.text() != '' and self.ui.port_le.text() != '' and self.ui.username_le.text() != '' and self.ui.password_le.text() != '':
            self.ui.add_btn.setEnabled(True)
        else:
            self.ui.add_btn.setEnabled(False)

    @pyqtSlot()
    def cancel(self):
        self.ui.name_le.clear()
        self.ui.port_le.clear()
        self.ui.username_le.clear()
        self.ui.password_le.clear()
        self.hide()

    @pyqtSlot()
    def add(self):
        self.parent.parent.add_template(self.ui.name_le.text(), self.ui.port_le.text(), self.ui.username_le.text(),
                          self.ui.password_le.text())
        self.cancel()
        self.parent.update_template_list()


class ManageWindow(QFrame):
    def __init__(self, parent):
        super(ManageWindow, self).__init__()
        self.parent = parent
        self.ui = Ui_ManageWindow()
        self.ui.setupUi(self)
        self.ui.add_template_dialog = AddTemplateDialog(self)
        self.ui.add_template_btn.clicked.connect(lambda: self.ui.add_template_dialog.show())
        self.ui.remove_template_btn.clicked.connect(self.remove_template)
        self.ui.add_stands_dialog = AddStandsDialog(self)
        self.ui.add_stands_btn.clicked.connect(self.show_add_stands_dialog)
        self.update_template_list()
        self.update_stands_list()

    @pyqtSlot()
    def show_add_stands_dialog(self):
        self.ui.add_stands_dialog.update_templates()
        self.ui.add_stands_dialog.show()

    @pyqtSlot()
    def remove_template(self):
        a = self.ui.templates_list.currentItem()
        if self.ui.templates_list.currentItem():
            self.parent.remove_template(self.ui.templates_list.currentItem().text())
        self.update_template_list()

    @pyqtSlot()
    def update_template_list(self):
        self.ui.templates_list.clear()
        for template in self.parent.templates:
            self.ui.templates_list.addItem(QListWidgetItem(template))

    @pyqtSlot()
    def update_stands_list(self):
        self.ui.stands_list.clear()
        for stand in self.parent.stands:
            self.ui.stands_list.addItem(QListWidgetItem(stand))


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.vlc_instance = vlc.Instance()
        with open('templates.json', 'r') as file:
            self.templates = json.load(file)
        with open('stands.json', 'r') as file:
            self.stands = json.load(file)
        self.manage_window = ManageWindow(self)
        self.mediaplayer: vlc.MediaPlayer = self.vlc_instance.media_player_new()
        if platform.system() == 'Linux':
            self.mediaplayer.set_xwindow(int(self.ui.media_frame.winId()))
        elif platform.system() == 'Windows':
            self.mediaplayer.set_hwnd(int(self.ui.media_frame.winId()))
        elif platform.system() == 'Darwin':
            self.mediaplayer.set_nsobject(int(self.ui.media_frame.winId()))

        self.ui.play_btn.clicked.connect(self.play_clicked)
        self.ui.stop_btn.clicked.connect(self.stop_clicked)
        self.ui.manage_btn.clicked.connect(self.show_manage_window)
        self.ui.splash = QSplashScreen(QPixmap('/home/skummer/Pictures/sticker1.png'))
        self.update_stands_list()
        self.ui.stands_list.currentTextChanged.connect(self.stand_selected)
        self.ui.search_le.textChanged.connect(self.update_stands_list)
        self.ui.goto_btn.clicked.connect(self.goto)

    @pyqtSlot()
    def goto(self):
        if self.ui.presets_le.currentItem():
            cam = ONVIFCamera(self.stands[self.ui.stands_list.currentItem().text()]['ip'],
                              user=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']][
                                  'username'],
                              passwd=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']][
                                  'password'], port=80)
            ptz = cam.create_ptz_service()
            cam.ptz.GotoPreset({'ProfileToken': self.ui.streams_cb.currentText(), 'PresetToken': self.ui.presets_le.currentItem().data(0x0100)})

    @pyqtSlot()
    def stand_selected(self):
        if 'streams' not in self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]:
            cam = ONVIFCamera(self.stands[self.ui.stands_list.currentItem().text()]['ip'], user=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['username'], passwd=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['password'], port=80)
            media = cam.create_media_service()
            profiles = cam.media.GetProfiles()
            self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['streams'] = {}
            for profile in profiles:
                stream = cam.media.GetStreamUri(
                {'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': 'RTSP'}, 'ProfileToken': profile.token}).Uri
                # stream = stream.replace('rtsp://', f'rtsp://{self.templates[self.stands[self.ui.stands_list.currentItem().text()]["template"]]["username"]}:{self.templates[self.stands[self.ui.stands_list.currentItem().text()]["template"]]["password"]}@')
                stream = f':{stream.split(":")[2]}'
                self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['streams'][profile.token] = stream
                with open('templates.json', 'w') as file:
                    json.dump(self.templates, file)
        self.ui.streams_cb.clear()
        for stream in self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['streams']:
            self.ui.streams_cb.addItem(stream)

    @pyqtSlot()
    def update_stands_list(self):
        self.ui.stands_list.clear()
        if self.ui.search_le.text() == '':
            for stand in self.stands:
                self.ui.stands_list.addItem(QListWidgetItem(stand))
        else:
            for stand in self.stands:
                add = True
                for idx, search_char in enumerate(self.ui.search_le.text()):
                    if stand[idx] != search_char:
                        add = False
                        break
                if add:
                    self.ui.stands_list.addItem(QListWidgetItem(stand))

    def add_stands(self, stands):
        for stand in stands:
            self.stands[stand] = stands[stand]
        with open('stands.json', 'w') as file:
            json.dump(self.stands, file)

    def remove_stands(self, stands):
        for stand in stands:
            del self.stands[stand]
        with open('stands.json', 'w') as file:
            json.dump(self.stands, file)

    def remove_template(self, name: str):
        if name in self.templates.keys():
            del self.templates[name]
        with open('templates.json', 'w') as file:
            json.dump(self.templates, file)

    def add_template(self, name: str, port: str | int, username: str, password: str):
        self.templates[name] = {
            'port': int(port),
            'username': username,
            'password': password
        }
        with open('templates.json', 'w') as file:
            json.dump(self.templates, file)

    @pyqtSlot()
    def show_manage_window(self):
        self.manage_window.show()

    @pyqtSlot()
    def play_clicked(self):
        token = self.ui.streams_cb.currentText()
        template = self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]
        postfix = template['streams'][token]
        stream = f'rtsp://{template["username"]}:{template["password"]}@{self.stands[self.ui.stands_list.currentItem().text()]["ip"]}{postfix}'
        print(stream)
        self.mediaplayer.set_media(self.vlc_instance.media_new(stream))
        print('Starting stream')
        self.mediaplayer.play()
        cam = ONVIFCamera(self.stands[self.ui.stands_list.currentItem().text()]['ip'], user=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['username'], passwd=self.templates[self.stands[self.ui.stands_list.currentItem().text()]['template']]['password'], port=80)
        ptz = cam.create_ptz_service()
        presets = cam.ptz.GetPresets({'ProfileToken': token})
        self.ui.presets_le.clear()
        for preset in presets:
            item = QListWidgetItem(preset['Name'])
            item.setData(0x0100, preset['token'])
            self.ui.presets_le.addItem(item)

    @pyqtSlot()
    def stop_clicked(self):
        self.mediaplayer.stop()


if __name__ == '__main__':
    if not exists('templates.json'):
        with open('templates.json', 'w') as file:
            json.dump({}, file)
    if not exists('stands.json'):
        with open('stands.json', 'w') as file:
            json.dump({}, file)

    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    # main_window.mediaplayer.set_media(main_window.vlc_instance.media_new('/home/skummer/Downloads/sample.mp4'))
    # main_window.mediaplayer.set_media(main_window.vlc_instance.media_new('rtsp://admin:1qaz2wsx@10.222.9.62:554/cam/realmonitor?channel=1&subtype=1&unicast=true&proto=Onvif'))
    # main_window.mediaplayer.play()
    sys.exit(app.exec())
