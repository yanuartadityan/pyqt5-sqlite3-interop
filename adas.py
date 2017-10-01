import sqlite3
import numpy as np
from scipy.io import savemat
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import *
from PyQt5.QtWidgets import (QApplication, QDialog, QMenu, QComboBox, QMessageBox, QCheckBox,
                             QMenuBar, QHBoxLayout, QVBoxLayout, QGridLayout, QFileDialog, QAction,
                             QLabel, QLineEdit, QTextEdit, QDialogButtonBox,
                             QGroupBox, QPushButton)


# global dicts for lookup
events_initial = {'lname': 'Search using ADAS decoded log file (.mat)',
                  'ldate': 'Search using upload date following format YYYY-MM-DD, e.g. 2017-05-30, etc',
                  'lvn': 'Search using vehicle registration number, e.g. JPP297, AES256, etc',
                  'ldil': 'Search using percentage of how centered the car (within detected lane markers) during the log',
                  'lsng': 'Search using number of host standing (stopping) and go',
                  'llc': 'Search using number of host changing lane',
                  'lvehl': 'Search using count of vehicle entering host lane',
                  'lvlhl': 'Search using count of vehicle leaving host lane',
                  'llm': 'Search using count of merged lane',
                  'lvrihl': 'Search using numbers of VRU in host lane',
                  'lvror': 'Search using numbers of VRU on the road',
                  'laor': 'Search using numbers of animals on the road',
                  'loihl': 'Search using count of obstacle in the host lane',
                  'loor': 'Search using count of obstacle on the road',
                  'lvss': 'Search using count of stand still vehicle'}

events_menu = {'lname': '&Log Name',
               'ldate': '&Upload Date',
               'lvn': '&Vehicle Number',
               'ldil': '&Drive in Lane',
               'lsng': '&Stop and Go',
               'llc': '&Lane Change',
               'lvehl': '&Vehicle Entering Host Lane',
               'lvlhl': '&Vehicle Leaving Host Lane',
               'llm': '&Lane Merge',
               'lvrihl': '&VRU in Host Lane',
               'lvror': '&VRU on Road',
               'laor': '&Animal on Road',
               'loihl': '&Obstacle in Host Lane',
               'loor': '&Obstacle on Road',
               'lvss': '&Vehicle Standstill'}

events_schema = {'lname': 'log_name',
                 'ldate': 'upload_date',
                 'lvn': 'vehicle',
                 'ldil': 'drive_in_lane',
                 'lsng': 'stop_and_go',
                 'llc': 'lane_change',
                 'lvehl': 'veh_enters_host_lane',
                 'lvlhl': 'veh_leaves_host_lane',
                 'llm': 'lane_merge',
                 'lvrihl': 'vru_in_host_lane',
                 'lvror': 'vru_on_road',
                 'laor': 'animal_on_road',
                 'loihl': 'obstacle_in_host_lane',
                 'loor': 'obstacle_on_road',
                 'lvss': 'vehicle_standstill'}


adas_tables = 'adas_events'


# Main dialog window with menu
class Dialog(QDialog):

    window_width = 1000
    window_height = 500
    def_border_left = 50
    def_border_top = 50

    # message
    MSG_DB_SUCCESS = "<p>The database has been loaded succesfully. <br/>" \
                     "All available schemas are available to be selected and used.</p>"
    MSG_DB_FAIL = "<p>Loaded database does not have ADAS schemas. <br/>" \
                  "Provide proper database. </p>"
    MSG_NOT_DB = "<p>Loaded file is not recognised as a SQL database. <br>Schema check " \
                 " routine will be ignored until a proper database is loaded </p>"
    MSG_SQL_EMPTY = "Make sure to provide at least one query"

    sql_template = "SELECT * FROM adas_events WHERE "

    def __init__(self, screen, parent=None):
        super(Dialog, self).__init__(parent=parent)

        # init
        self._query_val = []
        self._query_str = ''
        self.log_results = []
        self._limit = '1000'
        self._count = 0

        # screen related
        if screen:
            screen_temp = screen.size()
            self.screen_width = screen_temp.width()
            self.screen_height = screen_temp.height()
            print('App is shown in ' + screen.name())
            print('Size: %d x %d' % (self.screen_width, self.screen_height))
            self.border_left = (self.screen_width - self.window_width) * 0.5
            self.border_top = (self.screen_height - self.window_width) * 0.5
        else:
            self.border_left = self.def_border_left
            self.border_top = self.def_border_top

        # build menu and actions for the menu
        self.create_actions()
        self.create_query_actions_fast()
        self.create_menu()
        self.create_query_box()
        self.create_result_box()

        # build the layout (use grid)
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menuBar)
        main_layout.addWidget(self.qu_box)
        main_layout.addWidget(self.res_box)
        main_layout.addLayout(self.result_buttons)
        self.setLayout(main_layout)

        # 4. Adjust the top app layout dimension
        self.setGeometry(self.border_left, self.border_top, self.window_width, self.window_height)
        self.setWindowTitle('ADAS DB Finder 0.1')
        self.setWindowIcon(QIcon('icon\sql.png'))

    # ---------- actions, menu, layout and widgets
    def create_actions(self):
        self.act_exit = QAction('&Exit', self,
                                statusTip="Exit programme",
                                triggered=self.accept)
        self.act_exit.setStatusTip('Exit ADAS Finder...')

        self.act_open = QAction('&Open', self,
                                statusTip="Open a database",
                                triggered=self.open_db)
        self.act_open.setStatusTip('Open ADAS database...')

        self.act_about = QAction('&About', self,
                                 statusTip="Informations regarding the ADAS Log finder",
                                 triggered=self.about)
        self.act_about.setStatusTip('More informations about ADAS Finder...')

    def create_query_actions_fast(self):
        self.list_qu_actions = map(lambda x: QAction(x, self, triggered=self.open_qu_dialog), list(events_menu.values()))

    # ---------- all front-end GUI related
    def create_menu(self):
        self.menuBar = QMenuBar()

        # Menu options
        self.fiMenu = QMenu('&File')
        self.dbMenu = QMenu('&Database')
        self.quMenu = QMenu('&Add Query')
        self.heMenu = QMenu('&Help')

        self.quMenu.setDisabled(True)

        # Sub-menu actions
        self.menuBar.addMenu(self.fiMenu)
        self.fiMenu.addAction(self.act_exit)

        self.menuBar.addMenu(self.dbMenu)
        self.dbMenu.addAction(self.act_open)

        self.menuBar.addMenu(self.quMenu)
        self.quMenu.addActions(list(self.list_qu_actions))

        self.menuBar.addMenu(self.heMenu)
        self.heMenu.addAction(self.act_about)

    def create_query_box(self):
        # create a group for the query related stuffs
        self.qu_box = QGroupBox('Queries Configurations')
        self.qu_box.setFlat(False)

        # layouting and widgetting
        self.checkbox_layout = QGridLayout()

        self.query_text = QTextEdit("SELECT * FROM [table_name] WHERE [queries]")
        self.query_text.setDisabled(True)
        self.checkbox_layout.addWidget(self.query_text, 0, 0, 6, 2)

        self.bu1 = QPushButton('&Reset')
        self.bu2 = QPushButton('&Search')

        self.bu1.setDisabled(True)
        self.bu2.setDisabled(True)

        self.bu1.clicked.connect(self.clear_query)
        self.bu2.clicked.connect(self.submit_query)

        self.dynamic_checkboxes()

        # layout for the button box
        button_box = QHBoxLayout()
        button_box.addWidget(self.bu1)
        button_box.addWidget(self.bu2)
        button_box.addStretch()

        self.checkbox_layout.addLayout(button_box, 9, 7)
        self.checkbox_layout.setColumnStretch(0, 20)
        # layout.setColumnStretch(5, 5)

        self.qu_box.setLayout(self.checkbox_layout)

    def dynamic_checkboxes(self):

        max_row = 6

        # create all widgets
        self.cbes = list(map(lambda x: QCheckBox(x), list(events_menu.values())))

        # init by disable first
        count_row = 0
        count_col = 0
        for i in self.cbes:
            i.setChecked(False)
            i.setDisabled(True)
            self.checkbox_layout.addWidget(i, count_row, 5 + count_col)

            count_row += 1

            if count_row == max_row:
                count_col += 1
                count_row = 0

        # action
        for i in self.cbes:
            i.clicked.connect(self.open_qu_dialog)

    def create_result_box(self):
        self.res_box = QGroupBox('Filtered log files')

        # all widgets
        self.res_label = QTextEdit()
        self.res_label.setReadOnly(True)
        self.res_label.setText("\n".join(self.log_results))

        self.btn_export_csv = QPushButton('To CSV')
        self.btn_export_mat = QPushButton('To MAT')
        self.btn_clear = QPushButton('Clear')

        # v box
        self.local_v_box = QVBoxLayout()
        self.local_v_box.addWidget(self.res_label)

        # h box
        self.result_buttons = QHBoxLayout()
        self.result_buttons.addStretch()
        self.result_buttons.addWidget(self.btn_clear)
        self.result_buttons.addWidget(self.btn_export_csv)
        self.result_buttons.addWidget(self.btn_export_mat)

        # button actions
        self.btn_clear.clicked.connect(lambda: self.res_label.setText(''))
        self.btn_export_csv.clicked.connect(self.export_to_csv)
        self.btn_export_mat.clicked.connect(self.export_to_mat)

        # stack
        self.res_box.setLayout(self.local_v_box)

    # ---------- all mechanisms
    def qu_cbes_enable(self):
        # enable cbes
        for i in self.cbes:
            i.setDisabled(False)

    def qu_cbes_disable(self):
        # disable cbes
        for i in self.cbes:
            i.setDisabled(True)

    def qu_cbes_unchecked(self):
        # enable cbes
        for i in self.cbes:
            i.setChecked(False)

    def open_qu_dialog(self):

        sender = self.sender()
        print(sender.text())

        # if the open dialog request comes from checkbox
        # then check if the box is checked or not
        if isinstance(sender, QCheckBox):
            if not sender.isChecked():
                sender.setChecked(False)
                self.erase_query(sender.text())
                return
            else:
                pass

        choice = None
        for k, v in events_menu.items():
            if sender.text() == v:
                choice = k
                break

        if not choice:
            self.warning_box()

        # geometry of dialog window
        parent_geom = self.geometry()

        fix_width = 500
        fix_height = 160
        border_left = parent_geom.left() + parent_geom.width() / 2 - fix_width / 2
        border_top = parent_geom.top() + parent_geom.height() / 2 - fix_height / 2

        # spawn a child
        w = QueryDialog(choice, self)
        w.setGeometry(border_left, border_top, fix_width, fix_height)
        w.setFixedSize(fix_width, fix_height)
        w.setWindowIcon(QIcon('icon\query.png'))

        # use exec_, not show, to handle the modality (main window unaccessible while)
        # this widget is active
        w.exec_()

    def erase_query(self, sender_menu):
        # get the sender menu
        sender_id = ''
        for k, v in events_menu.items():
            if sender_menu == v:
                sender_id = k
                break

        # get the sender schema
        sender_schema = events_schema[sender_id]

        # !can be better
        self._query_val = [x for x in self._query_val if x[1] != sender_schema]
        self._query_str = ' '.join(list(map(lambda x: ' '.join(x), self._query_val)))
        self.count = len(self._query_val)

        if self.count == 0:
            self.clear_query()
        else:
            self.query_text.setText(self.sql_template + self._query_str)

    def erase_result_box(self):
        self.res_label.setText('')
        self.log_results = []
        self.res_box.setText('asdfsdf')

    def enable_front_end(self):
        self.quMenu.setDisabled(False)
        self.query_text.setDisabled(False)
        self.qu_cbes_enable()
        self.bu1.setDisabled(False)
        self.bu2.setDisabled(False)

    def warning_box(self):
        sender = self.sender()

        msg_wrng = "<p>Something wrong has happened in {}." \
                   "Make sure to code properly next time!</p>" \
                   "<p> Do you want to report the error?</p>".format(sender.text())

        reply = QMessageBox.question(self, "QMessageBox.question()",
                                     msg_wrng, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Yes:
            self.questionLabel.setText("Yes")
        elif reply == QMessageBox.No:
            self.questionLabel.setText("No")
        else:
            self.questionLabel.setText("Cancel")

    def about(self):
        msg_about = "<p><h1>The <b>ADAS Logfinder v.0.1</b></h1></p>" \
                    "<p><h4>SQLite3 based database finder for ADAS</h4></p>" \
                    "<p></p><p>This app can be used to search for all ADAS related logs within " \
                    "database. This is not a database generator as databases are automatically populated " \
                    "during the uploading state.</p>" \
                    "<br/>" \
                    "<b>Written using:</b>" \
                    "<br/>PyQt5" \
                    "<br/>Python {py_ver}<br/><br/>" \
                    "<br/>Make sure to report and file any found issues and bugs to:" \
                    "<p><i><b>Yanuar Tri Aditya Nugraha </b><a href='mailto:ytriadit@volvocars.com'>(Mail)</a>" \
                    "<br/>Active Safety Sensor A/V" \
                    "<br/>94414 Mölndal 72:6" \
                    "<br/>Copyrighted by <b>Volvo Cars</b></p>".format(py_ver='3.6')

        self.about_box = QMessageBox()
        self.about_box.about(self, "About Application", msg_about)

    # ---------- all sqlite3 related
    def open_db(self):
        file_name, _ = QFileDialog.getOpenFileName(self,
                                                   "Open ADAS Database",
                                                   "",
                                                   "All Files (*);;ADAS Database (*.db)")
        # if valid, then triggers sqlite3 connect
        if file_name:

            # load the database
            self.db = sqlite3.connect(file_name)
            self.check_db()

            if self.db_status:
                # enable the query
                QMessageBox.information(self, "Information", self.MSG_DB_SUCCESS)

                # enable front end
                self.enable_front_end()
            else:
                # do nothing
                if self.db_status_code == 1:
                    QMessageBox.information(self, "Warning", self.MSG_DB_FAIL)
                else:
                    QMessageBox.information(self, "Warning", self.MSG_NOT_DB)

                # let it go let it go
                pass

    def check_db(self):
        # sanity check
        try:
            c = self.db.cursor()
            c.execute("SELECT 1 FROM {tn} LIMIT 1".format(tn=adas_tables))

            # update db status
            self.db_status = True
            self.db_status_code = 0

        except sqlite3.DatabaseError as e:
            err_message = e.args[0]
            print(err_message)
            self.db_status = False
            if err_message.startswith('no such table'):
                self.db_status_code = 1     # sqlite3 db but table is nowhere to be found
            else:
                self.db_status_code = 2     # not a db

            pass

    def clear_query(self):
        self.query_text.setText("SELECT * FROM [table_name] WHERE [queries]")
        self._count = 0
        self._query_val = []
        self._query_str = ''

        # enable cbes
        self.qu_cbes_unchecked()

    def submit_query(self):

        if self._count > 0:
            self.submitted_sql_query = self.sql_template + self._query_str + ' LIMIT ' + self._limit
            print(self.submitted_sql_query)

            c = self.db.cursor()
            c.execute(self.submitted_sql_query)

            rows = c.fetchall()
            self.log_results = [x[1] for x in rows]
            self.res_label.setText("\n".join(self.log_results))
        else:
            QMessageBox.information(self, "Warning", self.MSG_SQL_EMPTY)

    def export_to_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Save Results to CSV",
                                                   "",
                                                   "All Files (*);;Comma Separated Values (*.csv)")

        if file_name:
            with open(file_name, mode='wt', encoding='utf-8') as file_handler:
                file_handler.write('\n'.join(self.log_results))

    def export_to_mat(self):
        file_name, _ = QFileDialog.getSaveFileName(self,
                                                   "Save Results to Matlab (*.mat) Compatible files",
                                                   "",
                                                   "All Files (*);;MATLAB .mat files (*.mat)")

        if file_name:
            temp = np.zeros((len(self.log_results),), dtype=np.object)
            temp[:1] = self.log_results
            savemat(file_name, mdict={'results': temp})

# Window for query search
class QueryDialog(QDialog):

    def __init__(self, choice, parent=None):
        super(QueryDialog, self).__init__(parent)

        self.choice = choice

        self.create_query_box()
        self.create_status_box()
        self.create_button_box()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.qubox)
        main_layout.addWidget(self.status)
        main_layout.addWidget(self.butbox)

        self.setLayout(main_layout)
        self.setWindowTitle(events_menu[self.choice].replace('&', ''))

    def closeEvent(self, event=None):
        sender = self.sender()

        if isinstance(sender, QCheckBox):
            checkbox_str = str(sender.text())

            idx = 0
            for k, v in events_menu.items():
                if v == checkbox_str:

                    curr_sender_len = len([x for x in self.parent()._query_val if x[1] == checkbox_str])

                    if curr_sender_len == 0:
                        self.parent().cbes[idx].setChecked(False)

                idx += 1

        self.close()

    def create_query_box(self):
        # glob
        self.d_operator = ['==', '>', '>=', '<', '<=', 'LIKE']
        self.q_operator = ['OR', 'AND']

        if self.choice in ['lname', 'ldate', 'lvn']:
            opr = [self.d_operator[5]]
        else:
            opr = self.d_operator[0:4]

        self.opr_label = QLabel('Operator')
        self.opr_list = QComboBox()
        self.opr_list.addItems(opr)

        self.val_label = QLabel('Values')
        self.val_value = QLineEdit()

        self.qopr_label = QLabel('Combinator')
        self.qopr_value = QComboBox()
        self.qopr_value.addItems(self.q_operator)

        # layout
        qu_layout = QHBoxLayout()
        qu_layout.addWidget(self.opr_label)
        qu_layout.addWidget(self.opr_list)
        qu_layout.setAlignment(self.opr_label, Qt.AlignLeft)
        qu_layout.setAlignment(self.opr_list, Qt.AlignLeft)

        qu_layout.addWidget(self.val_label)
        qu_layout.addWidget(self.val_value)
        qu_layout.setAlignment(self.val_label, Qt.AlignCenter)
        qu_layout.setAlignment(self.val_value, Qt.AlignCenter)

        qu_layout.addWidget(self.qopr_label)
        qu_layout.addWidget(self.qopr_value)
        qu_layout.setAlignment(self.qopr_label, Qt.AlignRight)
        qu_layout.setAlignment(self.qopr_value, Qt.AlignRight)

        # Alignment
        qu_layout.addStretch(1)

        # update the qubox
        self.qubox = QGroupBox('Query')
        self.qubox.setLayout(qu_layout)

    def create_status_box(self):
        self.status = QGroupBox('Information')
        self.st_label = QVBoxLayout()
        _, t = self.get_verbose()
        lbl = QLabel(t)
        self.st_label.addWidget(lbl)
        self.status.setLayout(self.st_label)

    def create_button_box(self):
        self.butbox = QDialogButtonBox(QDialogButtonBox.Ok)

        self.butbox.accepted.connect(self.generate_single_query)

    def generate_single_query(self):

        self.MSG_QUERY_EMPTY = "<p>Make sure the value is not empty</p>"

        val_operator = self.opr_list.currentText()
        val_value = self.val_value.displayText()
        val_qoperator = self.qopr_value.currentText()

        self.query_tuple = (val_operator, val_value, val_qoperator)

        # close the dialog after sending the tuple data back to main window
        if self.check_query_val(self.query_tuple):
            print('data is {}'.format(self.query_tuple))
            self.update_main_query()
            self.close()
        else:
            QMessageBox.information(self, "Warning", self.MSG_QUERY_EMPTY)

    def check_query_val(self, qu_tuple):
        if not qu_tuple[1]:
            return False
        else:
            return True

    def update_main_query(self):

        self.parent().sql_template = "SELECT * FROM adas_events WHERE "

        # only use OR/AND if query count is more than 0
        if self.parent()._count == 0:
            qopr = ''
        else:
            qopr = self.query_tuple[2]

        opr = self.query_tuple[0]
        sch = events_schema[self.choice]

        if self.choice in ['lname', 'ldate', 'lvn']:
            val = "'%" + self.query_tuple[1] + "%'"
        else:
            val = self.query_tuple[1]

        built_query = [qopr, sch, opr, val]

        # update the related query
        print(self.parent()._query_val)
        self.parent()._query_val = self.parent()._query_val + [built_query]
        print(self.parent()._query_val)
        self.parent()._query_str = ' '.join(list(map(lambda x: ' '.join(x), self.parent()._query_val)))
        self.parent().query_text.setDisabled(False)
        self.parent().query_text.setText(self.parent().sql_template + self.parent()._query_str)
        self.parent()._count += 1

        # enable the selection code
        idx = 0
        for k in events_menu:
            if self.choice == k:
                self.parent().cbes[idx].setDisabled(False)
                self.parent().cbes[idx].setChecked(True)
            idx += 1

        self.close()

    def get_verbose(self):
        print(self.choice)
        print(events_initial[self.choice])

        return self.choice, events_initial[self.choice]

    def who_am_i(self):
        sender = self.sender()
        print(sender.text())


# main routine
if __name__ == '__main__':
    import sys

    # create an app
    app = QApplication(sys.argv)

    # get screen size
    screen_info = app.primaryScreen()

    # spawn main window
    # dialog = Dialog(screen_info)
    # dialog.show()

    dialog = Dialog(screen_info)
    dialog.show()

    # loop the program
    sys.exit(dialog.exec_())
