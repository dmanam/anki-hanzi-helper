from aqt import mw
from aqt.utils import showInfo, chooseList, getText
from aqt.qt import *
from anki.storage import Collection

from collections import defaultdict

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
    decks = mw.addonManager.getConfig(__name__)['unsuspender']
    characters = set()
    for deck_id, field in decks.items():
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ? AND queue != -1', deck_id):
            note = mw.col.getNote(row[0]) # get_note
            characters |= set(note[field])
    n_updated = 0
    for deck_id, field in decks.items():
        for row in mw.col.db.execute('SELECT id, nid FROM cards WHERE did = ? AND queue = -1', deck_id):
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

def markUnique():
    decks = mw.addonManager.getConfig(__name__)['uniquemarker']
    nids = {}
    counts = defaultdict(lambda: 0)
    uniquecount = 0
    nonuniquecount = 0
    for deck_id, [pinyinfield, markfield] in decks.items():
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            nids[row[0]] = [pinyinfield, markfield]
    for nid in nids:
        note = mw.col.getNote(nid) # get_note
        counts[note[pinyinfield]] += 1
    for nid, [pinyinfield, markfield] in nids.items():
        note = mw.col.getNote(nid) # get_note
        if counts[note[pinyinfield]] == 1:
            note[markfield] = "unique"
            note.flush() # col.update_note(note)
            uniquecount += 1
        else:
            note[markfield] = ""
            note.flush() # col.update_note(note)
            nonuniquecount += 1
    dialog = QMessageBox()
    dialog.setText("Finished marking %i unique notes and %i non-unique notes" % (uniquecount, nonuniquecount))
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def copyInfo():
    decks = mw.addonManager.getConfig(__name__)['unsuspender']
    num = 0
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            note = mw.col.getNote(row[0]) # get_note
            did = False
            if note["Key"] != "":
                note["Recognition"] = "true"
                did |= True
            if note["XHZ Meaning"] != "":
                note["XHZ"] = "true"
                did |= True
            note.flush()
            if did:
                num += 1
    dialog = QMessageBox()
    dialog.setText("did %i" % num)
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def doMerge():
    pairs = defaultdict(lambda: {"rec": None, "xhz": None, "skip": False})
    toomany = []
    toofew = []
    toremove = []
    for row0 in mw.col.db.execute('SELECT id FROM notes WHERE tags LIKE "% duplicate %"'):
        for row in mw.col.db.execute('SELECT id, nid, did FROM cards WHERE nid = ?', row0[0]):
            note = mw.col.getNote(row[1])
            hanzi = note["Simplified"]
            deck = "rec" if int(row[2]) == 1660023039388 else "xhz"
            if pairs[hanzi][deck] != None:
                pairs[hanzi]["skip"] = True
                toomany += [hanzi]
            else:
                pairs[hanzi][deck] = row
    for hanzi, pair in pairs.items():
        rec = pair["rec"]
        xhz = pair["xhz"]
        if pair["skip"]:
            continue
        if not rec or not xhz:
            toofew += [hanzi]
            continue
        recnote = mw.col.getNote(rec[1])
        xhznote = mw.col.getNote(xhz[1])
        for key in ["Key", "Traditional", "Pinyin", "Pinyin ASCII", "Meaning", "Part of speech", "Audio", "Homophone", "Homograph", "Sentence Simplified", "Sentence Traditional", "Sentence Simplified Cloze", "Sentence Traditional Cloze", "Sentence Pinyin", "Sentence Pinyin ASCII", "Sentence Meaning", "Sentence Audio", "Sentence Image"]:
            xhznote[key] = recnote[key]
        xhznote.tags += recnote.tags
        mw.col.db.execute('UPDATE cards SET nid = ? WHERE id = ?', xhz[1], rec[0])
        mw.col.db.execute("DELETE FROM notes WHERE id = ?", rec[1])
        mw.col.db.execute("DELETE FROM cards WHERE nid = ?", rec[1])
        xhznote.flush()
    dialog = QMessageBox()
    dialog.setText("Skipped " + str(toomany) + " for having too many and " + str(toofew) + " for having too few")
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

menu = QMenu('Hanzi Helper', mw)
menu_show_decks = menu.addAction('Show Deck IDs')
menu_unsuspend = menu.addAction('Run Unsuspender')
menu_unique = menu.addAction('Mark Pinyin Uniqueness')

menu_show_decks.triggered.connect(showDecks)
menu_unsuspend.triggered.connect(unsuspend)
menu_unique.triggered.connect(markUnique)

mw.form.menuTools.addMenu(menu)
