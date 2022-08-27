from aqt import mw
from aqt.utils import showInfo, chooseList, getText
from aqt.qt import *
from anki.storage import Collection

def showDecks():
    text = ""
    for deck in mw.col.decks.all():
        text += "%s: %i\n" % (deck["name"], deck["id"])
#   for deck_name, deck_id in mw.col.decks.all_names_and_ids():
#       text += "%s: %i\n" % (deck_name, deck_id)
    dialog = QMessageBox()
    dialog.setWindowTitle("Deck IDs")
    dialog.setText(text)
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def unsuspend():
    decks = mw.addonManager.getConfig(__name__)['decks']
    characters = set()
    for deck_id, field in decks.items():
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = %s AND queue != -1' % deck_id):
            note = mw.col.getNote(row[0]) # get_note
            characters |= set(note[field])
    n_updated = 0
    for deck_id, field in decks.items():
        for row in mw.col.db.execute('SELECT id, nid FROM cards WHERE did = %s AND queue = -1' % deck_id):
            note = mw.col.getNote(row[1]) # get_note
            if set(note[field]).issubset(characters):
                note.addTag("auto_unsuspended")
                note.flush() # col.update_note(note)
                card = mw.col.getCard(row[0]) # get_card
                card.queue = card.type
                card.flush() # col.update_card(card)
                n_updated += 1
    dialog = QMessageBox()
    dialog.setText("Unsuspended %i cards using %i unique characters" % (n_updated, len(characters)))
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

menu = QMenu('Hanzi Unsuspender', mw)
menu_show_decks = menu.addAction('Show Deck IDs')
menu_unsuspend = menu.addAction('Run')

menu_show_decks.triggered.connect(showDecks)
menu_unsuspend.triggered.connect(unsuspend)

mw.form.menuTools.addMenu(menu)
