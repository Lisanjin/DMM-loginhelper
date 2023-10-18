import sys,os
from PyQt5.QtWidgets import QApplication,QWidget,QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,QDesktopWidget,QMessageBox,QComboBox,QHBoxLayout
from PyQt5.QtGui import QIcon
import re
import json
import requests
from urllib.parse import quote_plus 
import webbrowser
from qt_material import apply_stylesheet



class User_Setting():
    def __init__(self) -> None:
        user_setting_file =  open("setting.json",'r',encoding='utf8') 
        self.user_setting = json.load(user_setting_file)
        user_setting_file.close()
        self.proxies_port = self.user_setting['代理端口']
        self.game_list = self.user_setting['游戏列表']
        self.first = True if self.user_setting.get('首次启动') == '是' else False

        account_file =  open("account.json",'r',encoding='utf8')
        self.account = json.load(account_file) 
        account_file.close()
    
    def updata(self):
        self.user_setting['首次启动'] = '否'  

        with open("setting.json", 'w', encoding='utf8') as user_setting_file:
            json.dump(self.user_setting, user_setting_file, ensure_ascii=False, indent=4)  # 将数据写回文件

    def updata_account(self,account):
        self.account = account
        with open("account.json", 'w', encoding='utf8') as account_file:
            json.dump(self.account, account_file, ensure_ascii=False, indent=4)


class DMMGame:
    
    @staticmethod
    def get_login_page_json(response:requests.Response) -> json:
        html_text = response.text
        start_of_json = html_text.find('<script id="__NEXT_DATA__" type="application/json">')+51
        json_data = json.loads(html_text[start_of_json:html_text.find('</script>',start_of_json)])
        return json_data

    def __init__(self,email:str,password:str,proxies_port) -> None:
        self.login_status_code = ''
        if not email or not password: raise ValueError('邮箱和密码不能为空')
        
        self.session = requests.session()
        self.session.proxies = {
                    'http': 'http://127.0.0.1:'+proxies_port,
                    'https': 'http://127.0.0.1:'+proxies_port,
                }

        self.login_id = email
        self.password = password
    
    def fanza_login(self, target:str) -> str:
        # 初始化url
        login_url = 'https://accounts.dmm.co.jp/service/login/password/'
        game_path = f'/play/{target}/'
        login_path = 'https%3A%2F%2Fpc-play.games.dmm.co.jp'+quote_plus(game_path)
        fanza_game_url = f'https://pc-play.games.dmm.co.jp/{game_path}'
        # 获取登录token
        response = self.session.get(
            login_url+f'=/path={login_path}',
            allow_redirects=False)
        print(response)
        json_data = DMMGame.get_login_page_json(response)
        login_data = {
            'token' : json_data['props']['pageProps']['token'],
            'login_id' : self.login_id,
            'password' : self.password,
            'path' : login_path
        }
        print(login_data)
        # 登录
        login_success = False
        response = self.session.post(login_url+'authenticate',data=login_data)
        print(response)
        with open("st.html","w",encoding='utf8') as f:
                f.write(response.text)
        if '2段階認証' in response.text:
            response = self.session.get(response.url,allow_redirects=False)
            json_data = self.get_login_page_json(response)
            totp_data = {
                'totp' : input('2段階認証, Please enter the code: '),
                'token' : json_data['props']['pageProps']['token'],
                'path' : login_path
            }
            response = self.session.post(
                login_url.replace('password/','totp/authenticate'),
                data=totp_data)
            if 'ログイン前のページへ遷移' in response.text:
                login_success = True
            else:
                json_data = self.get_login_page_json(response)
                return json_data['props']['pageProps']['error'][0]
        elif response.url == (login_url+f'=/path={login_path}'):
            json_data = self.get_login_page_json(response)
            return json_data['props']['pageProps']['error'][0]
        else:
            login_success = True
        
        # 访问游戏网址获取osapi ifr网址
        if login_success:
            response = self.session.get(fanza_game_url)
            pattern = r'(//osapi\.dmm\.com/gadgets/ifr[^"]+)'
            match = re.search(pattern, response.text)
            return 'https:' + match.group(1).replace('amp;', '') 
    
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('添加账号')
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()

        # 窗口移动到中间
        screen_geometry = QDesktopWidget().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        # Email输入框
        self.email_label = QLabel('Email:')
        self.email_input = QLineEdit()
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)

        # 密码输入框
        self.password_label = QLabel('密码:')
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        # 登录按钮
        self.login_button = QPushButton('登录')
        self.login_button.clicked.connect(self.add_account)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def add_account(self):
        # 在此处添加登录逻辑，可以将输入的email和密码传递给后端进行验证
        email = self.email_input.text()
        password = self.password_input.text()

        self.showMessage("账号添加成功",email)
        self.showWelcomeWindow(email)
       
        
    def showMessage(self, title, message):
        QMessageBox.information(self,message, title,QMessageBox.Ok)

    def showWelcomeWindow(self, email):
        self.hide()  # 隐藏登录窗口

        # 返回主窗口
        main_window = MainWindow()
        main_window.show()  # 显示主窗口

class MainWindow(QWidget):
    def __init__(self,setting):
        super().__init__()
        self.setting=setting
        self.initUI()
        

    def initUI(self):
        if self.setting.first:
            QMessageBox.warning(self, '警告',
'''
为了你的账号安全，如果不确信该软件的来源是否可靠
        请到github下载源代码自行编译
https://github.com/Lisanjin/DMM-loginhelper
使用记事本打开account.json和setting.json配置后使用
'''
                                )
            self.setting.updata()
        
        
        self.setWindowTitle('神绊！启动！')
        self.setGeometry(100, 100, 450, 200)
        

        self.main_layout = QHBoxLayout()
        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()
        self.right_up_layout = QHBoxLayout()
        self.right_down_layout = QHBoxLayout()
        
        # 创建账号列表下拉框
        self.account_combo = QComboBox()
        
        for account in self.setting.account:
            self.account_combo.addItem(account['email'])

        self.account_combo.setFixedWidth(200)
          

        # 创建游戏列表下拉框
        self.game_combo = QComboBox()
        for game_name in self.setting.game_list:
            if game_name[0] !='':
                self.game_combo.addItem(game_name[0])
            else:
                self.game_combo.addItem(game_name[1])

        self.game_combo.setFixedWidth(200)
        
        self.start_button = QPushButton('启动')
        self.start_button.clicked.connect(self.game_start)
        self.start_button.setFixedSize(100, 30)

        self.add_button = QPushButton('添加')
        self.add_button.clicked.connect(self.add_account)
        self.add_button.setFixedSize(65, 30)

        self.delete_button = QPushButton('删除')
        self.delete_button.clicked.connect(self.delete_account)
        self.delete_button.setFixedSize(65, 30)
        self.delete_button.setStyleSheet('background-color: gray; color: white;border: 1px solid gray;')

        self.left_layout.addWidget(self.account_combo)
        self.left_layout.addWidget(self.game_combo)

        self.right_up_layout.addStretch(1)
        self.right_up_layout.addWidget(self.delete_button)
        self.right_up_layout.addWidget(self.add_button)
        self.right_up_layout.addStretch(1)

        self.right_down_layout.addStretch(1)
        self.right_down_layout.addWidget(self.start_button)
        self.right_down_layout.addStretch(1)

        self.right_layout.addLayout(self.right_up_layout)
        self.right_layout.addLayout(self.right_down_layout)

        self.main_layout.addStretch(2)
        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addStretch(1)
        self.main_layout.addLayout(self.right_layout)
        self.main_layout.addStretch(3)
        
        
        self.setLayout(self.main_layout)

        # 窗口移动到中间
        screen_geometry = QDesktopWidget().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def message(self):
        pass

    def add_account(self):
        dialog = AddWindow(self)
        result = dialog.exec_()  # 显示对话框
        if result == QDialog.Accepted:
            QMessageBox.information(self, 'Success', '添加成功', QMessageBox.Ok)
            self.left_layout.removeWidget(self.account_combo)
            self.account_combo.deleteLater()
            
            self.account_combo = QComboBox()
        
            for account in self.setting.account:
                self.account_combo.addItem(account['email'])

            self.account_combo.setFixedWidth(200)

            self.left_layout.insertWidget(0, self.account_combo)



    def delete_account(self):
        current_account = self.account_combo.currentText()  

        for account in self.setting.account:
            if account['email'] == current_account:
                self.setting.account.remove(account)
        self.updata_account(self.setting.account)
        QMessageBox.information(self, 'Success', '删除成功', QMessageBox.Ok)
        self.left_layout.removeWidget(self.account_combo)
        self.account_combo.deleteLater()
            
        self.account_combo = QComboBox()
        
        for account in self.setting.account:
            self.account_combo.addItem(account['email'])

        self.account_combo.setFixedWidth(200)

        self.left_layout.insertWidget(0, self.account_combo)




    def game_start(self):
        self.start_button.setText('启动中')
        self.start_button.setEnabled(False)
        self.start_button.update()

        # 获取账号下拉框中当前选中项的文本
        current_account = self.account_combo.currentText()  
        current_game = self.game_combo.currentText()
        
        password = ''
        for account in self.setting.account:
            if account['email'] == current_account:
                password = account['password']

        proxies_port = self.setting.proxies_port

        
        DG = DMMGame(current_account, password,proxies_port)

        url = DG.fanza_login(current_game)

        webbrowser.open(url)

        self.start_button.setText('启动')
        self.start_button.setEnabled(True)

    def updata_account(self,account):
        self.setting.updata_account(account)

class AddWindow(QDialog):
    def __init__(self,MainWindow):
        super().__init__()
        self.mainwindow = MainWindow
        self.setWindowTitle('添加账号')
        self.setGeometry(200, 200, 300, 150)

        screen_geometry = QDesktopWidget().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
        layout = QVBoxLayout()
        self.email_label = QLabel('Email:')
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_edit)
        
        self.password_label = QLabel('Password:')
        self.password_edit = QLineEdit()
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_edit)
        

        self.add_button = QPushButton('添加')
        self.add_button.clicked.connect(self.add_account)
        layout.addWidget(self.add_button)
        
        self.setLayout(layout)

    def add_account(self):
        email_text = self.email_edit.text()
        password_text = self.password_edit.text()
        
        new_data={'email':email_text,"password":password_text}
        new_account_list = self.mainwindow.setting.account
        new_account_list.append(new_data)
        self.mainwindow.updata_account(new_account_list)

        self.accept()

        

if __name__ == '__main__':
    user_setting = User_Setting()

    app = QApplication(sys.argv)
    main_window = MainWindow(user_setting)
    apply_stylesheet(app, theme='light_red.xml')

    icon = QIcon("furau.ico")
    main_window.setWindowIcon(icon)

    main_window.show() 
    sys.exit(app.exec_())

#nuitka --mingw64 --standalone --onefile --show-progress --windows-disable-console --plugin-enable=pyqt5 --include-package-data=qt_material --windows-icon-from-ico=furau.ico --output-filename=大咪咪多号登录.exe DMM.py