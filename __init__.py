from aqt import mw
from aqt.utils import showInfo, chooseList, getText
from aqt.qt import *
from anki.storage import Collection

from collections import defaultdict
import os
import math

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

def parseInt(s, default=math.inf):
    try:
        return int(s)
    except ValueError:
        return default

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
    conf = mw.addonManager.getConfig(__name__)
    decks = conf['decks']
    field = conf['fields']['hanzi']
    characters = set()
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ? AND queue != -1', deck_id):
            note = mw.col.getNote(row[0]) # get_note
            characters |= set(note[field])
    n_updated = 0
    for deck_id in decks:
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
    conf = mw.addonManager.getConfig(__name__)
    decks = conf['decks']
    hanzifield = conf['fields']['hanzi']
    pinyinfield = conf['fields']['pinyin']
    markfield = conf['fields']['pinyin unique']
    rankfield = conf['fields']['frequency ranking']
    homophonefield = conf['fields']['homophones']
    homophonerankfield = conf['fields']['homophone frequency rank']
    nids = set()
    chars = defaultdict(lambda: [])
    uniquecount = 0
    nonuniquecount = 0
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            nids.add(row[0])
    for nid in nids:
        note = mw.col.getNote(nid) # get_note
        chars[note[pinyinfield]] += [(note[hanzifield], parseInt(note[rankfield]))]
        chars[note[pinyinfield]].sort(key=lambda x: x[1])
    for nid in nids:
        note = mw.col.getNote(nid) # get_note
        homs = chars[note[pinyinfield]]
        if len(homs) == 1:
            note[markfield] = "unique"
            note.flush() # col.update_note(note)
            uniquecount += 1
        else:
            note[markfield] = ""
            note[homophonefield] = ', '.join(x[0] for x in homs)
            rank = parseInt(note[rankfield])
            ranks = [x[1] for x in homs]
            if rank != math.inf or len(set(ranks)) == len(ranks):
                note[homophonerankfield] = str(ranks.index(rank) + 1)
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

def markHSK():
    decks = mw.addonManager.getConfig(__name__)['unsuspender']
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            note = mw.col.getNote(row[0]) # get_note
            if note.hasTag("HSKv3_789"):
                note["HSKv3 Level"] = "7"
            for i in range(6,0,-1):
                if note.hasTag("HSK%i" % i):
                    note["HSK Level"] = str(i)
                if note.hasTag("HSKv3_%i" % i):
                    note["HSKv3 Level"] = str(i)
            note.flush()
    dialog = QMessageBox()
    dialog.setText("ok")
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def markFrequency():
    import csv
    conf = mw.addonManager.getConfig(__name__)
    decks = conf['decks']
    wordfield = conf['fields']['hanzi']
    rankfield = conf['fields']['frequency ranking']
    pctfield = conf['fields']['frequency percentage']
    filename = os.path.join(__location__, "freq.tsv")
    freqlist = []
    total = 0
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file, delimiter='\t')
        for word, freqstr in reader:
            freq = int(freqstr)
            total += freq
            freqlist += [(word, freq)]
    freqlist.sort(key=lambda x: -x[1])
    freqdict = {}
    for i in range(len(freqlist)):
        word, freq = freqlist[i]
        freqdict[word] = (i+1, freq / total)
    notes = set()
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            notes.add(row[0])
    marked = 0
    unmarked = 0
    for nid in notes:
        note = mw.col.getNote(nid) # get_note
        if (word := note[wordfield]) in freqdict:
            rank, ratio = freqdict[word]
            note[rankfield] = str(rank)
            note[pctfield] = "%.2g" % (ratio * 100)
            note.flush()
            marked += 1
        else:
            unmarked += 1
    dialog = QMessageBox()
    dialog.setText("Marked %i words with frequency information and left %i words without" % (marked, unmarked))
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def markKey():
    import csv
    conf = mw.addonManager.getConfig(__name__)
    decks = conf['decks']
    keyfield = conf['fields']['key']
    wordfield = conf['fields']['hanzi']
    rankfield = conf['fields']['frequency ranking']
    hskfield = conf['fields']['hsk level']
    hskv3field = conf['fields']['hskv3 level']
    filename = os.path.join(__location__, "order.tsv")
    orderdict = defaultdict(lambda: math.inf)
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file, delimiter='\t')
        for word, order in reader:
            orderdict[word] = int(order)
    notes = set()
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            notes.add(row[0])
    notesbyorder = list(notes)
    def keyfn(nid, swap):
        note = mw.col.getNote(nid) # get_note
        word = note[wordfield]
        charorder = max(orderdict[char] for char in list(word))
        order = orderdict[word]
        rank = parseInt(note[rankfield])
        hsk = parseInt(note[hskfield])
        hskv3 = parseInt(note[hskv3field])
        middle = [(min(charorder, order), order), rank]
        if swap:
            middle.reverse()
        return [min(hsk, hskv3)] + middle + [max(hsk, hskv3)]
    notesbyorder.sort(key=lambda x: keyfn(x, False))
    notesbyrank = sorted(notesbyorder, key=lambda x: keyfn(x, True))
    seen = set()
    notelist = []
    for i in range(len(notesbyorder)):
        for ls in notesbyorder, notesbyrank:
            if ls[i] not in seen:
                notelist += [ls[i]]
                seen.add(ls[i])
    for i in range(len(notelist)):
        note = mw.col.getNote(notelist[i]) # get_note
        note[keyfield] = str(i)
        note.flush()
    dialog = QMessageBox()
    dialog.setText("Marked %i notes" % len(notelist))
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

def markClassifiers():
    import csv
    conf = mw.addonManager.getConfig(__name__)
    decks = conf['decks']
    wordfield = conf['fields']['hanzi']
    clfield = conf['fields']['classifiers']
    filename = os.path.join(__location__, "classifiers.tsv")
    cldict = {}
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file, delimiter='\t')
        for word, classifier in reader:
            cldict[word] = classifier
    notes = set()
    for deck_id in decks:
        for row in mw.col.db.execute('SELECT nid FROM cards WHERE did = ?', deck_id):
            notes.add(row[0])
    count = 0
    for noteid in notes:
        note = mw.col.getNote(noteid) # get_note
        if note[wordfield] in cldict:
            count += 1
            note[clfield] = cldict[note[wordfield]]
            note.flush()
    dialog = QMessageBox()
    dialog.setText("Marked %i notes" % count)
    dialog.setStandardButtons(QMessageBox.Ok)
    dialog.exec()

menu = QMenu('Hanzi Helper', mw)
menu_show_decks = menu.addAction('Show Deck IDs')
menu_unsuspend = menu.addAction('Run Unsuspender')
menu_unique = menu.addAction('Mark And Rank Homophones')
menu_freq = menu.addAction('Mark Word Frequency')
menu_key = menu.addAction('Mark Key')
menu_classifiers = menu.addAction('Mark Classifiers')

menu_show_decks.triggered.connect(showDecks)
menu_unsuspend.triggered.connect(unsuspend)
menu_unique.triggered.connect(markUnique)
menu_freq.triggered.connect(markFrequency)
menu_key.triggered.connect(markKey)
menu_classifiers.triggered.connect(markClassifiers)

mw.form.menuTools.addMenu(menu)
