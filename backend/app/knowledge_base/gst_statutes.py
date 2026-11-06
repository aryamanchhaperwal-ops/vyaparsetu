"""
Curated knowledge base of official Indian Goods and Services Tax (GST) statutes,
CBIC circulars, and standard accounting rules for MSMEs.
"""

from typing import List, Dict

GST_STATUTORY_CORPUS: List[Dict[str, str]] = [
    {
        "id": "SEC-7-IGST",
        "title": "Section 7, IGST Act 2017: Inter-State Supply",
        "citation": "Section 7 of Integrated Goods and Services Tax Act, 2017",
        "content": (
            "Supply of goods or services where the location of the supplier and the place of supply are in "
            "two different States, two different Union territories, or a State and a Union territory shall be treated "
            "as a supply of goods or services in the course of inter-State trade or commerce. Attracts IGST."
        ),
        "keywords": "inter-state, igst, different state, place of supply, interstate, outside state"
    },
    {
        "id": "SEC-8-IGST",
        "title": "Section 8, IGST Act 2017: Intra-State Supply",
        "citation": "Section 8 of Integrated Goods and Services Tax Act, 2017",
        "content": (
            "Supply of goods or services where the location of the supplier and the place of supply are in the same State "
            "or same Union territory shall be treated as intra-State supply. Attracts Central Tax (CGST) and State Tax (SGST) in equal shares."
        ),
        "keywords": "intra-state, cgst, sgst, same state, local supply, intrastate"
    },
    {
        "id": "SEC-16-CGST",
        "title": "Section 16, CGST Act 2017: Eligibility and Conditions for Taking ITC",
        "citation": "Section 16(2) of Central Goods and Services Tax Act, 2017",
        "content": (
            "Every registered person is entitled to take credit of input tax charged on supply of goods or services used or intended to be used "
            "in the course or furtherance of business. Conditions: (a) possession of a tax invoice or debit note; (aa) details furnished in GSTR-1 "
            "and communicated in GSTR-2B; (b) receipt of goods or services; (c) tax charged actually paid to Government; (d) return filed under section 39."
        ),
        "keywords": "itc, input tax credit, conditions, gstr-2b, tax invoice, claiming itc, eligible credit"
    },
    {
        "id": "SEC-17-5-CGST",
        "title": "Section 17(5), CGST Act 2017: Blocked Credits",
        "citation": "Section 17(5) of Central Goods and Services Tax Act, 2017",
        "content": (
            "Input tax credit shall NOT be available in respect of: (a) motor vehicles for transportation of persons having approved seating capacity "
            "of not more than 13 persons; (b) supply of food and beverages, outdoor catering, beauty treatment, health services; (c) membership of a club, "
            "health and fitness centre; (h) goods lost, stolen, destroyed, written off or disposed of by way of gift or free samples."
        ),
        "keywords": "blocked itc, blocked credit, section 17(5), food, beverages, catering, car, motor vehicle, gift, stolen"
    },
    {
        "id": "SEC-31-CGST",
        "title": "Section 31, CGST Act 2017: Tax Invoice Requirements",
        "citation": "Section 31 of Central Goods and Services Tax Act, 2017",
        "content": (
            "A registered person supplying taxable goods shall issue a tax invoice showing the description, quantity and value of goods, "
            "tax charged thereon and other prescribed particulars (including GSTIN of supplier and recipient, consecutive serial number, date, HSN code)."
        ),
        "keywords": "tax invoice, bill, invoice particulars, gstin, serial number, mandatory fields"
    },
    {
        "id": "SEC-49-CGST",
        "title": "Section 49 & 49A/B, CGST Act 2017: Order of Utilization of Input Tax Credit",
        "citation": "Section 49, 49A and 49B of Central Goods and Services Tax Act, 2017",
        "content": (
            "Input tax credit on account of Integrated Tax (IGST) shall first be utilized towards payment of IGST, and the remaining amount, if any, "
            "towards CGST and SGST in any order. CGST credit cannot be utilized towards payment of SGST, and SGST credit cannot be utilized towards CGST."
        ),
        "keywords": "itc setoff, order of utilization, payment of tax, cross utilization, cgst against sgst"
    },
    {
        "id": "SEC-170-CGST",
        "title": "Section 170, CGST Act 2017: Rounding Off of Tax",
        "citation": "Section 170 of Central Goods and Services Tax Act, 2017",
        "content": (
            "The amount of tax, interest, penalty, fine or any other sum payable, and the amount of refund or any other sum due, "
            "under the provisions of this Act shall be rounded off to the nearest rupee and, for this purpose, where such amount involves a fraction of a rupee "
            "consisting of fifty paise or more, it shall be increased to one rupee and if such fraction is less than fifty paise it shall be disregarded."
        ),
        "keywords": "round off, rounding, section 170, 50 paise, nearest rupee, decimal"
    },
    {
        "id": "RULE-59-GSTR1",
        "title": "Rule 59, CGST Rules 2017: Form and Manner of Furnishing Outward Supplies (GSTR-1)",
        "citation": "Rule 59 of Central Goods and Services Tax Rules, 2017",
        "content": (
            "The details of outward supplies of goods or services required to be furnished under section 37 shall be furnished in FORM GSTR-1 "
            "electronically. Due date is 11th of the succeeding month for monthly filers and 13th of the month succeeding the quarter for QRMP taxpayers. "
            "Includes Table 4 (B2B), Table 5 (Interstate B2C large > 2.5L), Table 7 (B2C Small), and Table 12 (HSN summary)."
        ),
        "keywords": "gstr-1, gstr1, due date, table 4, table 7, hsn summary, outward supply return"
    },
    {
        "id": "RULE-61-GSTR3B",
        "title": "Rule 61, CGST Rules 2017: Monthly Return (GSTR-3B)",
        "citation": "Rule 61 of Central Goods and Services Tax Rules, 2017",
        "content": (
            "Every registered person required in FORM GSTR-3B shall furnish return electronically on or before the 20th day of the month succeeding "
            "such calendar month. Form GSTR-3B summarizes outward supplies, reverse charge supplies, eligible and ineligible ITC, and tax payment."
        ),
        "keywords": "gstr-3b, gstr3b, monthly return, due date 20th, tax payment return, self assessment"
    }
]

