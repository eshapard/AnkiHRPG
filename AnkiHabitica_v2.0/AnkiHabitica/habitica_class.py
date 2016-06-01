#!/usr/bin/python
from habitica_api import HabiticaAPI
import os, sys, json, datetime
from aqt import *
from aqt.main import AnkiQt

class Habitica(object):
    
    def __init__(self, user_id, api_token, profile, iconfile, conffile):
        self.api = HabiticaAPI(user_id, api_token)
        self.profile = profile
        self.iconfile = iconfile
        self.conffile = conffile
        self.name = 'Anki User'
        self.lvl = 0
        self.xp = 0
        self.gp = 0
        self.hp = 0
	self.ht = 50
        self.mp = 0
        self.stats = {}
        self.hrpg_attempt = 0
	self.hnote = {}
	self.habit_checked = {}
	for habit in ["Anki Points"]:
	    self.habit_checked[habit] = False

    def hrpg_showInfo(self, text):
        #display a small message window with an OK Button
        parent = aqt.mw.app.activeWindow() or aqt.mw
        icon = QMessageBox.Information
        mb = QMessageBox(parent)
        mb.setText(text)
        if os.path.isfile(self.iconfile):
            mb.setIconPixmap(QPixmap(self.iconfile))
        else:
            mb.setIcon(icon)
        mb.setWindowModality(Qt.WindowModal)
        mb.setWindowTitle("Anki Habitica")
        b = mb.addButton(QMessageBox.Ok)
        b.setDefault(True)
	return mb.exec_()

    def hrpg_tooltip(self, text):
        utils.tooltip(_(text), period=1500)


    def get_user_object(self):
        return self.api.user()

    def update_stats(self):
        #self.hrpg_tooltip("Connecting to Habitica")
        try:
            user = self.get_user_object()
        except:
            self.hrpg_showInfo("Unable to log in to Habitica.\n\nCheck that you have the correct user-id and api-token in\n%s.\n\nThese should not be your username and password.\n\nPost at github.com/eshapard/AnkiHRPG if this issue persists." % (self.conffile))
            return
        self.name = user['profile']['name']
        self.stats = user['stats']
        self.lvl = self.stats['lvl']
        self.xp = self.stats['exp']
        self.gp = self.stats['gp']
        self.hp = self.stats['hp']
        self.mp = self.stats['mp']
        return

    def score_anki_points(self, habit):
        return self.api.perform_task(habit, "up")

    def update_anki_habit(self, habit):
        #return self.api.alter_task("Anki Points", True, False, None, None, None, "int", None)
        data = {'up': True, 'down': False, 'attribute': 'int'}
        return self.api.update_task(habit, data)

    def check_anki_habit(self, habit):
        #Check to see that habitica habit is set up properly
        try:
            response = self.api.task(habit)
        except:
          return False
        if response['down'] or response['attribute'] != "int":
            try:
                self.update_anki_habit(habit)
                return True
            except:
                hrpg_showInfo("Your %s habit is not configured correctly yet.\nPlease set it to Up only and Mental attribute." % habit)
                return False
        return True

    def grab_scorecounter(self, habit):
	try:
            response = self.api.task(habit)
        except:
          return False
        #Try to grab the scorecount and last score date
        try: 
           self.hnote[habit] = json.loads(response['notes'])
           return True
	except:
           self.hnote[habit] = {'lastscoredate' : datetime.datetime.now().strftime('%Y-%m-%d'), 'scorecount': 0} 
           return False

    def post_scorecounter(self, habit):
	datastring = json.dumps(self.hnote[habit])
	#self.hrpg_showInfo(datastring)
	data = {"notes" : datastring}
        return self.api.update_task(habit, data)

    def scorecount_on_sync(self, x):
            for habit in self.habit_checked:
	        if self.habit_checked[habit]:
                    self.post_scorecounter(habit)
	        else:
                    self.grab_scorecounter(habit)

    def test_internet(self):
        #self.hrpg_tooltip("Testing Internet Connection")
        return self.api.test_internet()
            
    def make_score_message(self, new_lvl, new_xp, new_mp, new_gp, new_hp, streak_bonus=0, crit_multiplier=0, drop_text=None, drop_type=None):
        hrpgresponse = "Huzzah! You Get Points!\nWell Done %s!\n" % (self.name)
        #Check for increases and add to message
        if new_lvl > self.lvl:
            diff = int(new_lvl) - int(self.lvl)
            hrpgresponse += "\nYOU LEVELED UP! NEW LEVEL: %s" % (new_lvl)
	hrpgresponse += "\nHP: %s" % (int(self.hp))
	if new_hp > self.hp:
            diff = int(new_hp) - int(self.hp)
            hrpgresponse += "  +%s!" % (diff)
        hrpgresponse += "\nXP: %s" % (int(self.xp))
        if new_xp > self.xp:
            diff = int(new_xp) - int(self.xp)
            hrpgresponse += "  +%s!" % (diff)
        hrpgresponse += "\nGP: %s" % (round(self.gp, 2))
        if new_gp > self.gp:
            diff = int(new_gp) - int(self.gp)
            hrpgresponse += "  +%s!" % (diff)
        hrpgresponse += "\nMP: %s" % (int(self.mp))
        if new_mp > self.mp:
            diff = int(new_mp) - int(self.mp)
            hrpgresponse += "  +%s!" % (diff)
        #Check for drops, streaks, and critical hits
        if crit_multiplier:
            hrpgresponse += "\nCritical Hit! Bonus: +%s%%" % (int(float(crit_multiplier)))
        if streak_bonus:
            hrpgresponse += "\nStreak Bonus! +%s" % (int(streak_bonus))   
        if drop_text:
            hrpgresponse += "\nItem Drop! x%s" % (drop_text)
        if drop_type:
            hrpgresponse += "\nItem Drop! x%s" % (drop_type)
        #Show message box
        self.hrpg_showInfo(hrpgresponse)

        #update levels
        self.lvl = new_lvl
        self.xp = new_xp
        self.mp = new_mp
        self.gp = new_gp
        self.hp = new_hp
        return True

    def earn_points(self, habit):
	#check habit if is is unchecked
        if not self.habit_checked[habit]:
	    try:
                self.hrpg_tooltip("Checking Habit Score Counter")
	        self.check_anki_habit(habit)
                self.grab_scorecounter(habit)
		self.habit_checked[habit] = True
	    except:
                pass
        crit_multiplier = 0
        streak_bonus = 0
	drop_string = None
        drop_text = None
        drop_type = None
        try:
            msg = self.score_anki_points(habit)
            self.hnote[habit]['scorecount'] += 1
        except:
	    self.hrpg_showInfo("Sorry,\nI couldn't score your %s habit on Habitica.\nDon't worry, I'll remember your points and try again later." % habit)
            return False
        
        new_lvl = msg['lvl']
        new_xp = msg['exp']
        new_mp = msg['mp']
        new_gp = msg['gp']
        new_hp = msg['hp']
        if msg['_tmp']:
            if 'streakBonus' in msg['_tmp']:
                #streak
                streak_bonus = str(round((100 * msg['_tmp']['streakBonus']), 0))
            if 'crit' in msg['_tmp']:
                #critical
                crit_multiplier = str(round((100 * msg['_tmp']['crit']), 0))
                if 'drop' in msg['_tmp']:
                    #drop happened
		    drop_string = json.loads(msg['_tmp']['drop'])
                    #drop_text = msg['_tmp']['drop']['text']
                    #drop_type = msg['_tmp']['drop']['type']
	#try:
        #    self.post_scorecounter(habit) #update notes string of habit
        #except:
        #    pass
        return self.make_score_message(new_lvl, new_xp, new_mp, new_gp, new_hp, streak_bonus, crit_multiplier, drop_string, drop_type)
