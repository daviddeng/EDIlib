#!/usr/bin/env python
# encoding: utf-8
"""
convert SoftM INVOICE to VerySimpleInvoiceProtocol.

Created by Maximillian Dornseif on 2008-10-31.
Copyright (c) 2008, 2010 HUDORA. All rights reserved.
"""

from decimal import Decimal
import codecs
import copy
import edilib.softm.structure
import os
import os.path
import shutil
import husoftm.tools
import sys


class SoftMConverter(object):
    """Converts SoftM INVOICE files to very Simple Invoice Protocol."""

    def __init__(self):
        self.softm_record_list = None # whole set of records from SoftM

    def _convert_invoice_head(self, invoice_records):
        """Converts SoftM F1, F2 and varius others."""

        # needed entries from SoftM
        fa = invoice_records['FA']
        f1 = invoice_records['F1']
        f2 = invoice_records['F2']
        f3 = invoice_records['F3']
        f9 = invoice_records['F9']

        # erfasst_von - Name der Person oder des Prozesses, der den Auftrag in das System eingespeist hat.
        # F8 = Kontodaten

# <Bezogene Rechnungsnummer: 0>
# <verband: 0>,

# <Skontofähig USt 1: u'000000000053550'>,
# <waehrung: 'EUR'>,
# <ust1_fuer_skonto: Decimal('19.00')>,
# <ust2_fuer_skonto: Decimal('0.00')>,
# <eigene_iln_beim_kunden: u'4005998000007'>,
# <nettodatum: datetime.date(2009, 4, 7)>,
# <liefertermin: datetime.date(2009, 1, 21)>,
# <skonto1: Decimal('3.00')>,
# <skontobetrag1_ust1: Decimal('-1.610')>,


# <gesamtbetrag: Decimal('-53.550')>,
# <warenwert: Decimal('-45.000')>,
# <nettowarenwert1: Decimal('-45.000')>,
# <summe_rabatte:Decimal('0.000')>,
# <skontofaehig: Decimal('0.000')>,
# <summe_zuschlaege: Decimal('0.000')>,
# <steuerpflichtig1: Decimal('-45.000')>,
# <kopfrabatt1_prozent: Decimal('0.000')>,
# <steuerpflichtig USt 2: '000000000000000+'>,
# <kopfrabatt2_prozent: Decimal('0.000')>,
# <skontoabzug: Decimal('1.610')>,
# <kopfrabatt1_vorzeichen: '+'>,
# <kopfrabatt2_vorzeichen: '+'>,
# <kopfrabatt1: Decimal('0.000')>,
# <versandkosten1: Decimal('0.000')>,
# <mehrwertsteuer: Decimal('-8.550')>,
# <kopfrabatt2: Decimal('0.000')>,
# <steuerbetrag1: Decimal('-8.550')>,
# <TxtSlKopfrabatt1: ''>,
# <TxtSlKopfrabatt2: ''>,
# <KopfrabattUSt1: Decimal('0.000')>>

        kundennr = str(f1.rechnungsempfaenger)
        if not kundennr.startswith('SC'):
            kundennr = 'SC%s' % kundennr

        rechnungsnr=str(f1.rechnungsnr)
        if not rechnungsnr.startswith('RG'):
            rechnungsnr = 'RG%s' % rechnungsnr
        self.guid = rechnungsnr

        kopf = dict(
            guid=self.guid,
            kundennr=kundennr,
            name1=fa.rechnung_name1,
            name2=fa.rechnung_name2,
            name3=fa.rechnung_name3,
            strasse=fa.rechnung_strasse,
            land=husoftm.tools.land2iso(fa.rechnung_land),
            plz=fa.rechnung_plz,
            ort=fa.rechnung_ort,
            rechnungsnr=rechnungsnr,
            auftragsnr=str(f1.auftragsnr),
            kundenauftragsnr=f1.kundenbestellnummer,
            # <kundenbestelldatum: datetime.date(2008, 12, 16)>
            auftragsdatum=f1.auftragsdatum,
            rechnungsdatum=f1.rechnungsdatum,
            leistungsdatum=f1.liefertermin,
            infotext_kunde=' '.join([str(x) for x in (#f1.eigene_iln_beim_kunden.strip(),
                                                      f1.lieferantennummer.strip(),
                                                      ) if x]),
            versandkosten = int(f9.versandkosten1*100),
            warenwert = int(abs(f9.warenwert)*100), # in cent
            abschlag_prozent=f9.kopfrabatt1_prozent + f9.kopfrabatt2_prozent,
            # summe_zuschlaege=f9.summe_zuschlaege,
            # rechnungsbetrag='?5',
            rechnung_steuranteil=int(f9.mehrwertsteuer*100),
            steuer_prozent='19',
            zu_zahlen=int(abs(f9.gesamtbetrag)*100), # in cent

            zahlungstage=f1.nettotage,

            skonto_prozent=f1.skonto1,
            skontotage=f1.skontotage1,

            zu_zahlen_bei_skonto=int((abs(f9.gesamtbetrag)-abs(f1.skontobetrag1_ust1))*100), # in cent
            valutatage=f1.valutatage,
            valutadatum=f1.valutadatum,
            # debug
            skontofaehig=int(abs(f9.skontofaehig)*100),  # TODO: in cent?
            steuerpflichtig1=int(abs(f9.steuerpflichtig1)*100), # TODO: in cent?
            #skontofaehig=f9.skontofaehig,
            skontoabzug=f9.skontoabzug,
            )

        kopf['hint'] = dict(
            abschlag=int(f9.summe_rabatte*100), # = f9.kopfrabatt1 + f9.kopfrabatt2, in cent
            zahlungsdatum=f1.nettodatum,
            skontodatum=f1.skontodatum1,
            skontobetrag=int(abs(f9.skontoabzug)*100),
            # rechnungsbetrag_bei_skonto=, # excl. skonto
            rechnung_steueranteil_bei_skonto=kopf['zu_zahlen_bei_skonto']/1.19,
            steuernr_kunde=' '.join([f1.ustdid_rechnungsempfaenger, f1.steuernummer]).strip(),
            # debug
            skontofaehig_ust1=f1.skontofaehig_ust1,
            skonto1=f1.skonto1,
            skontobetrag1_ust1=f1.skontobetrag1_ust1,
        )

        warenempfaenger = str(f2.warenempfaenger)
        if not warenempfaenger.startswith('SC'):
            warenempfaenger = 'SC%s' % warenempfaenger

        kopf['lieferadresse'] = dict(
            kundennr=warenempfaenger,
            name1=f2.liefer_name1,
            name2=f2.liefer_name2,
            name3=f2.liefer_name3,
            strasse1=f2.liefer_strasse,
            plz=f2.liefer_plz,
            ort=f2.liefer_ort,
            land=husoftm.tools.land2iso(f2.liefer_land),  # fixup to iso country code
            #rec119_lieferaddr.internepartnerid = f2.warenempfaenger
        )

        if f2.liefer_iln and f2.liefer_iln != '0':
            kopf['lieferadresse']['iln'] = str(f2.liefer_iln)
        elif f2.iln_warenempfaenger and f2.iln_warenempfaenger != '0':
            kopf['lieferadresse']['iln'] = str(f2.iln_warenempfaenger)
        elif f2.besteller_iln and f2.besteller_iln != '0':
            kopf['lieferadresse']['iln'] = str(f2.besteller_iln)

        if f1.iln_rechnungsempfaenger and f1.iln_rechnungsempfaenger != '0':
            kopf['iln'] = str(f1.iln_rechnungsempfaenger)

        # Gutschrift oder Rechnung?
        if f1.belegart.lstrip('0') in ['380', '84']:
            kopf['transaktionsart'] = 'Rechnung'
        elif f1.belegart.lstrip('0') in ['381', '83']:
            kopf['transaktionsart'] = 'Gutschrift'
        else:
            raise ValueError("%s: Belegart %s unbekannt" % (rechnungsnr, f1.belegart.lstrip('0')))

        if f1.lieferscheinnr and int(f1.lieferscheinnr):
            kopf['lieferscheinnr'] = str(f1.lieferscheinnr)

        #rec900.steuerpflichtiger_betrag = abs(f9.steuerpflichtig1)
        #rec900.mwst_gesamtbetrag = abs(f9.mehrwertsteuer)
        #rec900.skontofaehiger_betrag = abs(f9.skontofaehig)
        #rec900.zu_und_abschlage = -1 * f9.summe_rabatte
        #rec900.zu_und_abschlage = f9.summe_zuschlaege - f9.summe_rabatte + f9.versandkosten1
        #if self.is_credit:
        #    rec900.zu_und_abschlage *= -1

        # FK = versandbedingungen und so
        # FX = kopfrabatt
        # FE = lieferbedingungen
        zeilen = []
        for k in ['FK', 'FE', 'FX', 'FV', 'FL', 'FN']:
            if k in invoice_records:
                zeile = []
                for i in range(1, 9):
                    text = getattr(invoice_records[k], 'textzeile%d' % i).strip()
                    if text:
                        zeile.append(text.strip())
                if zeile:
                    zeilen.append(' '.join(zeile))
        if zeilen:
            kopf['infotext_kunde'] = '\n'.join(zeilen).strip()

        if f1.ust2_fuer_skonto:
            print f1.ust2_fuer_skonto, kopf
            raise ValueError("%s hat einen zweiten Stuerersatz - das ist nicht unterstützt" % (rechnungsnr))
        if f1.skontodatum2 or f1.skontotage2 or f1.skonto2:
            print kopf
            raise ValueError("%s hat 2. Skontosatz - das ist nicht unterstützt" % (rechnungsnr))
        if f1.waehrung != 'EUR':
            print kopf
            raise ValueError("%s ist nicht in EURO - das ist nicht unterstützt" % (rechnungsnr))

        # ungenutzte Felder entfernen
        for k in kopf.keys():
            if kopf[k] == '':
                del kopf[k]
        # ungenutzte Felder entfernen
        for k in kopf['hint'].keys():
            if kopf['hint'][k] == '':
                del kopf['hint'][k]
        return kopf

    def _convert_invoice_position(self, position_records):
        """Converts SoftM F3 & F4 records to orderline"""

        f3 = position_records['F3']
        f4 = position_records['F4'] # Positionsrabatte

        line = dict(
            guid="%s-%s" % (self.guid, f3.positionsnr),
            menge=int(f3.menge),
            artnr=f3.artnr,
            kundenartnr=f3.artnr_kunde,
            name=f3.artikelbezeichnung.strip(),
            infotext_kunde=f3.artikelbezeichnung_kunde.strip(),
            einzelpreis = int(abs(f3.verkaufspreis)*100),
            positionswert = int(abs(f3.wert_netto)*100), # - incl rabatte?, in cent
            # debug:
            skontierfaehig=f3.skontierfaehig,
        )

        if f3.ean and int(f3.ean):
            line['ean']=f3.ean

        # FP = positionstext
        # FR = positionsrabatttext
        zeilen = []
        for k in [u'FP', u'FR']:
            if k in position_records.keys():
                zeile = []
                for i in range(1, 9):
                    text = getattr(position_records[k], 'textzeile%d' % i).strip()
                    if text:
                        zeile.append(text)
                if zeile:
                    zeilen.append(' '.join(zeile).strip())
        if zeilen:
            line['infotext_kunde'] = ' '.join([line['infotext_kunde']] + zeilen).strip()

        if f3.wert_netto != f3.wert_brutto:
            print line
            raise ValueError("%s hat Positionsrabatt - das ist nicht unterstützt" % (rechnungsnr))

        # ungenutzte Felder entfernen
        for k in line.keys():
            if line[k] == '':
                del line[k]

        return line

    def _convert_invoice(self, softm_record_slice):
        """Handles a SoftM invoice. Works on a slice of an INVOICE list, which
        contains the relavant stuff for the actual invoice."""

        softm_records = dict(softm_record_slice)
        kopf = self._convert_invoice_head(softm_records)

        # the now we have to extract the per invoice records from softm_record_list
        # every position starts with a F3 record
        tmp_softm_record_list = copy.deepcopy(softm_record_slice)

        # remove everything until we hit the first F3
        while tmp_softm_record_list and tmp_softm_record_list[0] and tmp_softm_record_list[0][0] != 'F3':
            tmp_softm_record_list.pop(0)

        # process positions
        kopf['orderlines'] = []
        while tmp_softm_record_list:
            # slice of segment untill the next F3
            position = [tmp_softm_record_list.pop(0)]
            while tmp_softm_record_list and tmp_softm_record_list[0] and tmp_softm_record_list[0][0] != 'F3':
                position.append(tmp_softm_record_list.pop(0))

            # process position
            kopf['orderlines'].append(self._convert_invoice_position(dict(position)))

        return kopf

    def _convert_invoices(self):
        """Handles the invoices of an SoftM invoice list."""

        softm_records = dict(self.softm_record_list)

        # now we have to extract the per invoice records from self.softm_record_list
        # every position starts with a F1 record
        tmp_softm_record_list = copy.copy(self.softm_record_list)

        # remove everything until we hit the first F1
        while tmp_softm_record_list and tmp_softm_record_list[0] and tmp_softm_record_list[0][0] != 'F1':
            tmp_softm_record_list.pop(0)

        # create sub-part of whole invoice (list) that represents one single invoice
        invoices = []
        while tmp_softm_record_list:
            # slice of segment until the next F1
            invoice = [tmp_softm_record_list.pop(0)]
            while tmp_softm_record_list and tmp_softm_record_list[0] and tmp_softm_record_list[0][0] != 'F1':
                invoice.append(tmp_softm_record_list.pop(0))

            # process invoice
            invoices.append(self._convert_invoice(invoice))
        return invoices

    def convert(self, data):
        """Parse INVOICE file and save result in workfile."""

        # If we handle a collection of single invoices here, we have to split them into pieces and
        # provide a header for them.

        self.softm_record_list = edilib.softm.structure.parse_to_objects(data.split('\n'))
        return self._convert_invoices()


def main():
    converter = SoftMConverter()
    converter.convert('/Users/md/code2/git/DeadTrees/workdir/backup/INVOIC/RG00994.TXT')
    for f in sorted(os.listdir('/Users/md/code2/git/DeadTrees/workdir/backup/INVOIC/'), reverse=True):
        if not f.startswith('RG'):
            continue
        # print f, os.path.join('/Users/md/code2/git/DeadTrees/workdir/backup/INVOIC/', f)
        converter = SoftMConverter()
        converter.convert(os.path.join('/Users/md/code2/git/DeadTrees/workdir/backup/INVOIC/', f))

# RG821130 ist nen tolles Beispiel für ne Gutschrift

if __name__ == '__main__':
    main()