from kivy.config import Config
Config.set('kivy', 'keyboard_mode', 'dock')
Config.set('graphics', 'fullscreen', 'auto')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
import threading
import lire_valeur
import send_sms
import time
import read_analog
import manage_contact

# Sous-classe DebouncedTextInput pour éviter la double saisie
class DebouncedTextInput(TextInput):
    def __init__(self, **kwargs):
        super(DebouncedTextInput, self).__init__(**kwargs)
        self.last_insert = ''
        self.last_time = 0
        self.debounce_duration = 0.3  # 300 ms

    def insert_text(self, substring, from_undo=False):
        current_time = time.time()
        if substring == self.last_insert and (current_time - self.last_time) <= self.debounce_duration:
            return
        super(DebouncedTextInput, self).insert_text(substring, from_undo)
        self.last_insert = substring
        self.last_time = current_time

class ContactScreen(Screen):
    def __init__(self, **kwargs):
        super(ContactScreen, self).__init__(**kwargs)
        self.last_submit_time = 0
        scroll_view = ScrollView()
        self.layout = BoxLayout(orientation='vertical',size_hint_y=1.5, spacing=5)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        self.name_contact = DebouncedTextInput(hint_text='Nom du contact', input_type='text')
        self.num_contact = DebouncedTextInput(hint_text='Numéro du contact', input_type='tel')
        self.mail_contact = DebouncedTextInput(hint_text='Mail du contact', input_type='text')
        self.submit_button = Button(text='Ajouter contact')
        self.submit_button.bind(on_press=self.add_contact)

        # Adding a back button
        self.back_button = Button(text='Retour')
        self.back_button.bind(on_press=self.go_back)

        self.layout.add_widget(self.name_contact)
        self.layout.add_widget(self.num_contact)
        self.layout.add_widget(self.mail_contact)
        self.layout.add_widget(self.submit_button)
        self.layout.add_widget(self.back_button)


        #self.add_widget(self.layout)

        # Add the BoxLayout to the ScrollView
        scroll_view.add_widget(self.layout)

        # Add the ScrollView to the main screen
        self.add_widget(scroll_view)

    def add_contact(self, instance):
        name_contact = self.name_contact.text
        num_contact = self.num_contact.text
        mail_contact = self.mail_contact.text

        contact=(name_contact,mail_contact,num_contact)
        manage_contact.ajouter_contact(contact, fichier='contacts.csv')

        self.name_contact.text = ''
        self.num_contact.text = ''
        self.mail_contact.text = ''

    def go_back(self, instance):
        # Navigate back to the HomeScreen
        self.manager.current = 'home'

class ContactListScreen(Screen):
    def __init__(self, **kwargs):
        super(ContactListScreen, self).__init__(**kwargs)
        self.layout = GridLayout(cols=2, spacing=10)  # Set the number of columns to 2
        self.contact_buttons = []
        self.selected_contact = None
        selected_phone_number = None

        # Populate contact buttons dynamically from the CSV file
        contacts = manage_contact.lire_contacts(fichier='contacts.csv')
        for contact in contacts:
            btn_contact = Button(text=f'{contact.get_nom()} - {contact.get_telephone()}')
            btn_contact.bind(on_press=lambda instance, contact=contact: self.select_contact(contact))
            self.contact_buttons.append(btn_contact)
            self.layout.add_widget(btn_contact)

        # Back button to return to the home screen
        back_button = Button(text='Retour')
        back_button.bind(on_press=self.go_back)
        self.layout.add_widget(back_button)

        self.add_widget(self.layout)

    def select_contact(self, contact):
        # Set the selected contact attribute
        selected_contact = contact
        #print(f"Selected contact: {contact.get_nom()} - {contact.get_telephone()}")
        ContactListScreen.selected_phone_number = contact.get_telephone()
        print(ContactListScreen.selected_phone_number)

    def go_back(self, instance):
        # Navigate back to the HomeScreen
        self.manager.current = 'home'

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super(HomeScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='horizontal')  # Modifier l'orientation en horizontal
        self.btn_layout = BoxLayout(orientation='vertical', size_hint=(None, 1), width=200)
        self.selected_contact = None
        self.value_labels = {}

        # Bouton pour configurer l'alarme
        btn_to_alarm = Button(text='Configurer Alarme')
        btn_to_alarm.bind(on_press=self.go_to_alarm_screen)
        self.btn_layout.add_widget(btn_to_alarm)

        # Bouton pour gérer les contacts
        btn_to_contact = Button(text='Gérer Contacts')
        btn_to_contact.bind(on_press=self.go_to_contact_screen)
        self.btn_layout.add_widget(btn_to_contact)

        # Bouton pour gérer les contacts
        btn_to_contact = Button(text='Voir Contacts')
        btn_to_contact.bind(on_press=self.go_to_contact_list_screen)
        self.btn_layout.add_widget(btn_to_contact)

        self.layout.add_widget(self.btn_layout)

        # Section pour afficher les valeurs
        self.values_layout = BoxLayout(orientation='vertical', size_hint=(1, 1))
        self.layout.add_widget(self.values_layout)

        self.add_widget(self.layout)

    def go_to_alarm_screen(self, instance):
        self.manager.current = 'alarm'

    def go_to_contact_screen(self, instance):
        self.manager.current = 'contact'

    def go_to_contact_list_screen(self, instance):
        print("Button pressed - Going to view contacts screen")
        contact_list_screen = self.manager.get_screen('contact_list')
        contact_list_screen.selected_contact = None  # Reset selected_contact when navigating to the contact list
        self.manager.current = 'contact_list'
        
    def update_value_labels(self, pin_number, value):
        # Vérifier si le label pour ce pin existe déjà
        if pin_number not in self.value_labels:
            # Créer un nouveau label et l'ajouter au dictionnaire
            label = Label(text=f'Pin {pin_number}: {value}')
            self.values_layout.add_widget(label)
            self.value_labels[pin_number] = label
        else:
            # Mettre à jour le label existant 
            self.value_labels[pin_number].text = f'Pin {pin_number}: {value}'

class AlarmScreen(Screen):
    def __init__(self, **kwargs):
        super(AlarmScreen, self).__init__(**kwargs)
        self.last_submit_time = 0
        self.layout = BoxLayout(orientation='vertical')
        self.value_input = DebouncedTextInput(hint_text='Valeur d\'alarme', input_type='number')
        self.pin_input = DebouncedTextInput(hint_text='Numéro du pin', input_type='number')
        self.submit_button = Button(text='Configurer')
        self.submit_button.bind(on_press=self.setup_alarm)

        self.layout.add_widget(self.value_input)
        self.layout.add_widget(self.pin_input)
        self.layout.add_widget(self.submit_button)

        self.add_widget(self.layout)

    def check_alarm(self, alarm_value, pin_number, home_screen):
        def update_ui(dt):
            if alarm_value != 1 or 0:
                gpio_value = read_analog.read_analog(pin_number)
            else:
                gpio_value = lire_valeur.read_value(pin_number)

            home_screen.update_value_labels(pin_number, gpio_value)

            if gpio_value < alarm_value:
                print(ContactListScreen.selected_phone_number)
                send_sms.sendSms('+'+str(ContactListScreen.selected_phone_number))

        # Ajouter un identifiant pour chaque intervalle programmé
        update_event = Clock.schedule_interval(update_ui, 1)

    def setup_alarm(self, instance):
        current_time = time.time()
        if current_time - self.last_submit_time > 0.3:  # Debounce de 0.3 secondes
            alarm_value = float(self.value_input.text)
            pin_number = int(self.pin_input.text)
            
            home_screen = self.manager.get_screen('home')
            alarm_thread = threading.Thread(target=self.check_alarm, args=(alarm_value, pin_number, home_screen))
            alarm_thread.daemon = True
            alarm_thread.start()

            self.manager.current = 'home'
            self.last_submit_time = current_time


class AlarmApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(AlarmScreen(name='alarm'))
        sm.add_widget(ContactScreen(name='contact'))
        sm.add_widget(ContactListScreen(name='contact_list'))  
        return sm

if __name__ == '__main__':
    AlarmApp().run()          
