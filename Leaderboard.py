import datetime
from datetime import date, timedelta
import threading
import requests
import json
from os.path import dirname, join, realpath
from PyQt5 import QtCore, QtGui, QtWidgets

from aqt import mw
from aqt.qt import *
from aqt.utils import showWarning

from .forms import Leaderboard
from .Stats import Stats
from .Achievement import start_achievement
from .config_manager import write_config
from .League import load_league
from .userInfo import start_user_info

try:
	nightmode = mw.pm.night_mode()
except:
	nightmode = False

with open(join(dirname(realpath(__file__)), "colors.json"), "r") as colors_file:
	data = colors_file.read()
colors_themes = json.loads(data)
colors = colors_themes["dark"] if nightmode else colors_themes["light"]


class start_main(QDialog):
	def __init__(self, season_start, season_end, parent=None):
		self.parent = parent
		self.season_start = season_start
		self.season_end = season_end
		QDialog.__init__(self, parent, Qt.Window)
		self.dialog = Leaderboard.Ui_dialog()
		self.dialog.setupUi(self)
		self.setupUI()

	def setupUI(self):
		config = mw.addonManager.getConfig(__name__)
		if config["refresh"] == True:
			self.dialog.Global_Leaderboard.setSortingEnabled(False)
			self.dialog.Friends_Leaderboard.setSortingEnabled(False)
			self.dialog.Country_Leaderboard.setSortingEnabled(False)
			self.dialog.Custom_Leaderboard.setSortingEnabled(False)
		else:
			header1 = self.dialog.Global_Leaderboard.horizontalHeader()
			header1.sortIndicatorChanged.connect(self.change_colors_global)
			header2 = self.dialog.Friends_Leaderboard.horizontalHeader()
			header2.sortIndicatorChanged.connect(self.change_colors_friends)
			header3 = self.dialog.Country_Leaderboard.horizontalHeader()
			header3.sortIndicatorChanged.connect(self.change_colors_country)
			header4 = self.dialog.Custom_Leaderboard.horizontalHeader()
			header4.sortIndicatorChanged.connect(self.change_colors_custom)

		tab_widget = self.dialog.Parent
		country_tab = tab_widget.indexOf(self.dialog.tab_3)
		subject_tab = tab_widget.indexOf(self.dialog.tab_4)
		tab_widget.setTabText(country_tab, config["country"])
		tab_widget.setTabText(subject_tab, config["subject"])
		self.dialog.Parent.setCurrentIndex(config['tab'])

		self.dialog.Global_Leaderboard.doubleClicked.connect(self.user_info_Global)
		self.dialog.Global_Leaderboard.setToolTip("Double click on user for more info.")
		self.dialog.Friends_Leaderboard.doubleClicked.connect(self.user_info_Friends)
		self.dialog.Friends_Leaderboard.setToolTip("Double click on user for more info.")
		self.dialog.Country_Leaderboard.doubleClicked.connect(self.user_info_Country)
		self.dialog.Country_Leaderboard.setToolTip("Double click on user for more info.")
		self.dialog.Custom_Leaderboard.doubleClicked.connect(self.user_info_Custom)
		self.dialog.Custom_Leaderboard.setToolTip("Double click on user for more info.")
		self.dialog.League.doubleClicked.connect(self.user_info_League)
		self.dialog.League.setToolTip("Double click on user for more info.")
		
		self.load_leaderboard()
		
	def load_leaderboard(self):

		### SYNC ###

		config = mw.addonManager.getConfig(__name__)
		url = 'https://ankileaderboard.pythonanywhere.com/sync/'
		config5 = config['subject'].replace(" ", "")
		config6 = config['country'].replace(" ", "")

		streak, cards, time, cards_past_30_days, retention, league_reviews, league_time, league_retention = Stats(self.season_start, self.season_end)

		data = {'Username': config['username'], "Streak": streak, "Cards": cards , "Time": time , "Sync_Date": datetime.datetime.now(),
		"Month": cards_past_30_days, "Subject": config5, "Country": config6, "Retention": retention,
		"league_reviews": league_reviews, "league_time": league_time, "league_retention": league_retention,
		"Token_v3": config["token"], "Version": "v1.6.0"}

		try:
			x = requests.post(url, data = data, timeout=20)
			if x.text == "Done!":
				pass
			else:
				showWarning(str(x.text))
		except:
			showWarning("Timeout error [load_leaderboard sync] - No internet connection, or server response took too long.", title="Leaderboard error")

		### ACHIEVEMENT ###

		achievement_streak = [7, 31, 100, 365, 500, 1000, 1500, 2000, 3000, 4000]
		if config["achievement"] == True and streak in achievement_streak:
			s = start_achievement(streak)
			if s.exec():
				pass

			write_config("achievement", False)

		### CLEAR TABLE ###

		self.dialog.Global_Leaderboard.setRowCount(0)
		self.dialog.Friends_Leaderboard.setRowCount(0)
		self.dialog.Country_Leaderboard.setRowCount(0)
		self.dialog.Custom_Leaderboard.setRowCount(0)
		self.dialog.League.setRowCount(0)

		### GET DATA ###

		new_day = datetime.time(int(config['newday']),0,0)
		time_now = datetime.datetime.now().time()
		if time_now < new_day:
			start_day = datetime.datetime.combine(date.today() - timedelta(days=1), new_day)
		else:
			start_day = datetime.datetime.combine(date.today(), new_day)

		url = 'https://ankileaderboard.pythonanywhere.com/getdata/'
		sortby = {"sortby": config["sortby"]}
		try:
			data = requests.post(url, data = sortby, timeout=20).json()
		except:
			data = []
			showWarning("Timeout error [load_leaderboard getData] - No internet connection, or server response took too long.", title="Leaderboard error")

		### LEAGUE ###

		# x = threading.Thread(target=load_league, args=(self, colors), daemon=True)
		# x.start()
		load_league(self, colors)
		time_remaining = self.season_end - datetime.datetime.now()
		tr_days = time_remaining.days
		tr_hours = int((time_remaining.seconds) / 60 / 60)

		if tr_days < 0:
			self.dialog.time_left.setText(f"The next season is going to start soon.")
		else:
			self.dialog.time_left.setText(f"{tr_days} days {tr_hours} hours remaining")
		self.dialog.time_left.setToolTip(f"Season start: {self.season_start} \nSeason end: {self.season_end} (local time)")

		### BUILD LEADERBOARD ###

		counter = 0
		friend_counter = 0
		country_counter = 0
		custom_counter = 0
		for i in data:
			username = i[0]
			streak = i[1]
			cards = i[2]
			time = i[3]
			sync_date = i[4]
			sync_date = sync_date.replace(" ", "")
			sync_date = datetime.datetime(int(sync_date[0:4]),int(sync_date[5:7]), int(sync_date[8:10]), int(sync_date[10:12]), int(sync_date[13:15]), int(sync_date[16:18]))
			try:
				month = int(i[5])
			except:
				month = ""
			subject = i[6]
			country = i[7]
			retention = i[8]
			try:
				retention = float(retention)
			except:
				retention = ""
			if sync_date > start_day and username not in config["hidden_users"]:
				counter = counter + 1

				rowPosition = self.dialog.Global_Leaderboard.rowCount()
				self.dialog.Global_Leaderboard.setColumnCount(6)
				self.dialog.Global_Leaderboard.insertRow(rowPosition)

				self.dialog.Global_Leaderboard.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(str(username)))

				item = QtWidgets.QTableWidgetItem()
				item.setData(QtCore.Qt.DisplayRole, int(cards))
				self.dialog.Global_Leaderboard.setItem(rowPosition, 1, item)

				item = QtWidgets.QTableWidgetItem()
				item.setData(QtCore.Qt.DisplayRole, float(time))
				self.dialog.Global_Leaderboard.setItem(rowPosition, 2, item)

				item = QtWidgets.QTableWidgetItem()
				item.setData(QtCore.Qt.DisplayRole, int(streak))
				self.dialog.Global_Leaderboard.setItem(rowPosition, 3, item)

				item = QtWidgets.QTableWidgetItem()
				item.setData(QtCore.Qt.DisplayRole, month)
				self.dialog.Global_Leaderboard.setItem(rowPosition, 4, item)

				item = QtWidgets.QTableWidgetItem()
				item.setData(QtCore.Qt.DisplayRole, retention)
				self.dialog.Global_Leaderboard.setItem(rowPosition, 5, item)

				self.dialog.Global_Leaderboard.resizeColumnsToContents()

				if country == config6 and country != "Country":
					country_counter = country_counter + 1

					rowPosition = self.dialog.Country_Leaderboard.rowCount()
					self.dialog.Country_Leaderboard.setColumnCount(6)
					self.dialog.Country_Leaderboard.insertRow(rowPosition)

					self.dialog.Country_Leaderboard.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(str(username)))

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(cards))
					self.dialog.Country_Leaderboard.setItem(rowPosition, 1, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, float(time))
					self.dialog.Country_Leaderboard.setItem(rowPosition, 2, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(streak))
					self.dialog.Country_Leaderboard.setItem(rowPosition, 3, item)


					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, month)
					self.dialog.Country_Leaderboard.setItem(rowPosition, 4, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, retention)
					self.dialog.Country_Leaderboard.setItem(rowPosition, 5, item)

					self.dialog.Country_Leaderboard.resizeColumnsToContents()

					if username in config['friends']:
						for j in range(self.dialog.Country_Leaderboard.columnCount()):
							self.dialog.Country_Leaderboard.item(country_counter-1, j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))

				if subject == config5 and subject != "Custom":
					custom_counter = custom_counter + 1

					rowPosition = self.dialog.Custom_Leaderboard.rowCount()
					self.dialog.Custom_Leaderboard.setColumnCount(6)
					self.dialog.Custom_Leaderboard.insertRow(rowPosition)

					self.dialog.Custom_Leaderboard.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(str(username)))

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(cards))
					self.dialog.Custom_Leaderboard.setItem(rowPosition, 1, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, float(time))
					self.dialog.Custom_Leaderboard.setItem(rowPosition, 2, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(streak))
					self.dialog.Custom_Leaderboard.setItem(rowPosition, 3, item)


					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, month)
					self.dialog.Custom_Leaderboard.setItem(rowPosition, 4, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, retention)
					self.dialog.Custom_Leaderboard.setItem(rowPosition, 5, item)

					self.dialog.Custom_Leaderboard.resizeColumnsToContents()

					if username in config['friends']:
						for j in range(self.dialog.Custom_Leaderboard.columnCount()):
							self.dialog.Custom_Leaderboard.item(custom_counter-1, j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))

				if username in config['friends']:
					friend_counter = friend_counter + 1

					rowPosition = self.dialog.Friends_Leaderboard.rowCount()
					self.dialog.Friends_Leaderboard.setColumnCount(6)
					self.dialog.Friends_Leaderboard.insertRow(rowPosition)

					self.dialog.Friends_Leaderboard.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(str(username)))

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(cards))
					self.dialog.Friends_Leaderboard.setItem(rowPosition, 1, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, float(time))
					self.dialog.Friends_Leaderboard.setItem(rowPosition, 2, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, int(streak))
					self.dialog.Friends_Leaderboard.setItem(rowPosition, 3, item)


					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, month)
					self.dialog.Friends_Leaderboard.setItem(rowPosition, 4, item)

					item = QtWidgets.QTableWidgetItem()
					item.setData(QtCore.Qt.DisplayRole, retention)
					self.dialog.Friends_Leaderboard.setItem(rowPosition, 5, item)

					self.dialog.Friends_Leaderboard.resizeColumnsToContents()

					for j in range(self.dialog.Global_Leaderboard.columnCount()):
						self.dialog.Global_Leaderboard.item(counter-1, j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))

				if username == config['username']:
					for j in range(self.dialog.Global_Leaderboard.columnCount()):
						self.dialog.Global_Leaderboard.item(counter-1, j).setBackground(QtGui.QColor(colors['USER_COLOR']))
					if config['friends'] != []:
						for j in range(self.dialog.Friends_Leaderboard.columnCount()):
							self.dialog.Friends_Leaderboard.item(friend_counter-1, j).setBackground(QtGui.QColor(colors['USER_COLOR']))
					if config['country'] != "Country":
						for j in range(self.dialog.Country_Leaderboard.columnCount()):
							self.dialog.Country_Leaderboard.item(country_counter-1, j).setBackground(QtGui.QColor(colors['USER_COLOR']))
					if config["subject"] != "Custom":
						for j in range(self.dialog.Custom_Leaderboard.columnCount()):
							self.dialog.Custom_Leaderboard.item(custom_counter-1, j).setBackground(QtGui.QColor(colors['USER_COLOR']))

		### Highlight first three places###

		if self.dialog.Global_Leaderboard.rowCount() >= 3:
			global first_three_global
			first_three_global = []
			for i in range(3):
				item = self.dialog.Global_Leaderboard.item(i, 0).text()
				first_three_global.append(item)

			for j in range(self.dialog.Global_Leaderboard.columnCount()):
				self.dialog.Global_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Global_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Global_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

		if self.dialog.Friends_Leaderboard.rowCount() >= 3:
			global first_three_friends
			first_three_friends = []
			for i in range(3):
				item = self.dialog.Friends_Leaderboard.item(i, 0).text()
				first_three_friends.append(item)

			for j in range(self.dialog.Friends_Leaderboard.columnCount()):
				self.dialog.Friends_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Friends_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Friends_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

		if self.dialog.Country_Leaderboard.rowCount() >= 3:
			global first_three_country
			first_three_country = []
			for i in range(3):
				item = self.dialog.Country_Leaderboard.item(i, 0).text()
				first_three_country.append(item)

			for j in range(self.dialog.Country_Leaderboard.columnCount()):
				self.dialog.Country_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Country_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Country_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

		if self.dialog.Custom_Leaderboard.rowCount() >= 3:
			global first_three_custom
			first_three_custom = []
			for i in range(3):
				item = self.dialog.Custom_Leaderboard.item(i, 0).text()
				first_three_custom.append(item)

			for j in range(self.dialog.Custom_Leaderboard.columnCount()):
				self.dialog.Custom_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Custom_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Custom_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

		### SCROLL ###

		current_ranking_list = []
		if config["scroll"] == True:
			for i in range(self.dialog.Global_Leaderboard.rowCount()):
				item = self.dialog.Global_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username']:
					userposition = self.dialog.Global_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Global_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)
					self.dialog.Global_Leaderboard.selectRow(current_ranking_list.index(item))
					self.dialog.Global_Leaderboard.clearSelection()

		current_ranking_list = []
		if config["scroll"] == True:
			for i in range(self.dialog.Friends_Leaderboard.rowCount()):
				item = self.dialog.Friends_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username']:
					userposition = self.dialog.Friends_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Friends_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)
					self.dialog.Friends_Leaderboard.selectRow(current_ranking_list.index(item))
					self.dialog.Friends_Leaderboard.clearSelection()

		current_ranking_list = []
		if config["scroll"] == True:
			for i in range(self.dialog.Country_Leaderboard.rowCount()):
				item = self.dialog.Country_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username']:
					userposition = self.dialog.Country_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Country_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)
					self.dialog.Country_Leaderboard.selectRow(current_ranking_list.index(item))
					self.dialog.Country_Leaderboard.clearSelection()

		current_ranking_list = []
		if config["scroll"] == True:
			for i in range(self.dialog.Custom_Leaderboard.rowCount()):
				item = self.dialog.Custom_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username']:
					userposition = self.dialog.Custom_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Custom_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)
					self.dialog.Custom_Leaderboard.selectRow(current_ranking_list.index(item))
					self.dialog.Custom_Leaderboard.clearSelection()

		if config["refresh"] == True:
			global t
			t = threading.Timer(120.0, self.load_leaderboard)
			t.daemon = True
			t.start()
		else:
			pass

	def change_colors_global(self):
		if self.dialog.Global_Leaderboard.rowCount() >= 3:
			config = mw.addonManager.getConfig(__name__)
			global first_three_global
			current_ranking_list = []

			for i in range(self.dialog.Global_Leaderboard.rowCount()):
				item = self.dialog.Global_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username'] and config["scroll"] == True:
					userposition = self.dialog.Global_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Global_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)

			for i in first_three_global:
				for j in range(self.dialog.Global_Leaderboard.columnCount()):
					if current_ranking_list.index(i) % 2 == 0:
						self.dialog.Global_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_LIGHT']))
					else:
						self.dialog.Global_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_DARK']))

					if i in config['friends']:
						self.dialog.Global_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))
					if i == config['username']:
						self.dialog.Global_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['USER_COLOR']))

			for j in range(self.dialog.Global_Leaderboard.columnCount()):
				self.dialog.Global_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Global_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Global_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

			first_three_global = []
			for i in range(3):
				item = self.dialog.Global_Leaderboard.item(i, 0).text()
				first_three_global.append(item)

	def change_colors_friends(self):
		if self.dialog.Friends_Leaderboard.rowCount() >= 3:
			config = mw.addonManager.getConfig(__name__)
			global first_three_friends
			current_ranking_list = []

			for i in range(self.dialog.Friends_Leaderboard.rowCount()):
				item = self.dialog.Friends_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username'] and config["scroll"] == True:
					userposition = self.dialog.Friends_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Friends_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)

			for i in first_three_friends:
				for j in range(self.dialog.Friends_Leaderboard.columnCount()):
					if current_ranking_list.index(i) % 2 == 0:
						self.dialog.Friends_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_LIGHT']))
					else:
						self.dialog.Friends_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_DARK']))

					if i == config['username']:
						self.dialog.Friends_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['USER_COLOR']))

			for j in range(self.dialog.Friends_Leaderboard.columnCount()):
				self.dialog.Friends_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Friends_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Friends_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

			first_three_friends = []
			for i in range(3):
				item = self.dialog.Friends_Leaderboard.item(i, 0).text()
				first_three_friends.append(item)

	def change_colors_country(self):
		if self.dialog.Country_Leaderboard.rowCount() >= 3:
			config = mw.addonManager.getConfig(__name__)
			global first_three_country
			current_ranking_list = []

			for i in range(self.dialog.Country_Leaderboard.rowCount()):
				item = self.dialog.Country_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username'] and config["scroll"] == True:
					userposition = self.dialog.Country_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Country_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)

			for i in first_three_country:
				for j in range(self.dialog.Country_Leaderboard.columnCount()):
					if current_ranking_list.index(i) % 2 == 0:
						self.dialog.Country_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_LIGHT']))
					else:
						self.dialog.Country_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_DARK']))

					if i in config['friends']:
						self.dialog.Country_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))
					if i == config['username']:
						self.dialog.Country_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['USER_COLOR']))

			for j in range(self.dialog.Country_Leaderboard.columnCount()):
				self.dialog.Country_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Country_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Country_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

			first_three_country = []
			for i in range(3):
				item = self.dialog.Country_Leaderboard.item(i, 0).text()
				first_three_country.append(item)

	def change_colors_custom(self):
		if self.dialog.Custom_Leaderboard.rowCount() >= 3:
			config = mw.addonManager.getConfig(__name__)
			global first_three_custom
			current_ranking_list = []

			for i in range(self.dialog.Custom_Leaderboard.rowCount()):
				item = self.dialog.Custom_Leaderboard.item(i, 0).text()
				current_ranking_list.append(item)
				if item == config['username'] and config["scroll"] == True:
					userposition = self.dialog.Custom_Leaderboard.item(current_ranking_list.index(item), 0)
					self.dialog.Custom_Leaderboard.scrollToItem(userposition, QAbstractItemView.PositionAtCenter)

			for i in first_three_custom:
				for j in range(self.dialog.Custom_Leaderboard.columnCount()):
					if current_ranking_list.index(i) % 2 == 0:
						self.dialog.Custom_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_LIGHT']))
					else:
						self.dialog.Custom_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['ROW_DARK']))

					if i in config['friends']:
						self.dialog.Custom_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['FRIEND_COLOR']))
					if i == config['username']:
						self.dialog.Custom_Leaderboard.item(current_ranking_list.index(i), j).setBackground(QtGui.QColor(colors['USER_COLOR']))

			for j in range(self.dialog.Custom_Leaderboard.columnCount()):
				self.dialog.Custom_Leaderboard.item(0, j).setBackground(QtGui.QColor(colors['GOLD_COLOR']))
				self.dialog.Custom_Leaderboard.item(1, j).setBackground(QtGui.QColor(colors['SILVER_COLOR']))
				self.dialog.Custom_Leaderboard.item(2, j).setBackground(QtGui.QColor(colors['BRONZE_COLOR']))

			first_three_custom = []
			for i in range(3):
				item = self.dialog.Custom_Leaderboard.item(i, 0).text()
				first_three_custom.append(item)

	def user_info_Global(self):
		for idx in self.dialog.Global_Leaderboard.selectionModel().selectedIndexes():
			row = idx.row()
		user_clicked = self.dialog.Global_Leaderboard.item(row, 0).text()
		mw.user_info = start_user_info(user_clicked)
		mw.user_info.show()
		mw.user_info.raise_()
		mw.user_info.activateWindow()

	def user_info_Friends(self):
		for idx in self.dialog.Friends_Leaderboard.selectionModel().selectedIndexes():
			row = idx.row()
		user_clicked = self.dialog.Friends_Leaderboard.item(row, 0).text()
		mw.user_info = start_user_info(user_clicked)
		mw.user_info.show()
		mw.user_info.raise_()
		mw.user_info.activateWindow()

	def user_info_Country(self):
		for idx in self.dialog.Country_Leaderboard.selectionModel().selectedIndexes():
			row = idx.row()
		user_clicked = self.dialog.Country_Leaderboard.item(row, 0).text()		
		mw.user_info = start_user_info(user_clicked)
		mw.user_info.show()
		mw.user_info.raise_()
		mw.user_info.activateWindow()

	def user_info_Custom(self):
		for idx in self.dialog.Custom_Leaderboard.selectionModel().selectedIndexes():
			row = idx.row()
		user_clicked = self.dialog.Custom_Leaderboard.item(row, 0).text()
		mw.user_info = start_user_info(user_clicked)
		mw.user_info.show()
		mw.user_info.raise_()
		mw.user_info.activateWindow()

	def user_info_League(self):
		for idx in self.dialog.League.selectionModel().selectedIndexes():
			row = idx.row()
		user_clicked = self.dialog.League.item(row, 0).text()
		mw.user_info = start_user_info(user_clicked)
		mw.user_info.show()
		mw.user_info.raise_()
		mw.user_info.activateWindow()

	def closeEvent(self, event):
		config = mw.addonManager.getConfig(__name__)
		if config["refresh"] == True:
			global t
			t.cancel()
			event.accept()
		else:
			event.accept()