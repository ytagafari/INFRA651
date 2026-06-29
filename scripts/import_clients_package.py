#!/usr/bin/env python3
"""Index clients_package folder and sync knowledge-base sheets for agent retrieval."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_CANDIDATES = [
    ROOT / "clients_package" / "clients_package",
    ROOT / "clients_package",
    ROOT / "knowledge-base" / "clients-package",
]

DEST = ROOT / "knowledge-base" / "clients-package"
SHEETS = ROOT / "knowledge-base" / "sheets"

DOCUMENTS = [
    ("DS-M740D", "Utilcell M740D Digital Load Cell 15-60t", "datasheet", "M740D",
     "m740d,load cell,digital,15-60t,truck scale,weighing,oiml,r60,rs485,ip68,utilcell",
     "datasheets/En-De_DS_M740D_Utilcell.pdf"),
    ("DS-M740-60T", "Utilcell M740 15-60t Load Cell Datasheet", "datasheet", "M740-60T",
     "m740,15-60t,truck scale,weighbridge,heavy capacity,load cell,utilcell",
     "datasheets/En-De_DS_M740-15-60t_Utilcell.pdf"),
    ("DS-WDESK-BL", "WDESK-BL Weighing Indicator", "datasheet", "WDESK-BL",
     "wdesk,indicator,display,weighing desk,utilcell,serie w",
     "datasheets/WDESK-BL_EN-1.pdf"),
    ("DS-SMART-DIGITAL", "Smart-Digital Utilcell Datasheet", "datasheet", "Smart-Digital",
     "smart digital,digital weighing,transmitter,utilcell",
     "datasheets/En-De_DS_Smart-Digital_Utilcell.pdf"),
    ("DS-CLM8", "CLM8 Product Datasheet", "datasheet", "CLM8",
     "clm8,utilcell,weighing,load cell,compact",
     "datasheets/CLM8_EN.pdf"),
    ("MKT-SW-GENERAL", "SensWEIGHT General Leaflet A3", "marketing", "SensWEIGHT",
     "sensweight,leaflet,overview,remote monitoring,iiot,weighing,24/7",
     "marketing/SensWEIGHT_Leaflet_A3_PRINT_READY.pdf"),
    ("MKT-SW-TRUCK", "SensWEIGHT Truck Scale Leaflet", "marketing", "SensWEIGHT,M740-60T",
     "sensweight,truck scale,weighbridge,digitalization,fleet",
     "marketing/SensWEIGHT_Leaflet_A3_TruckScalePRINT_READY.pdf"),
    ("MKT-SW-BELT", "SensWEIGHT Belt Scale Leaflet", "marketing", "SensWEIGHT",
     "sensweight,belt scale,conveyor,continuous weighing",
     "marketing/SensWEIGHT_BeltScale_Leaflet_A3_PRINT_READY.pdf"),
    ("MKT-SW-SILO", "SensWEIGHT Silo Leaflet", "marketing", "SensWEIGHT,SensSILO",
     "sensweight,silo,agriculture,storage,inventory,theft,structural,grain,cement",
     "marketing/SensWEIGHT_Leaflet_A3_SILOPRINT_READY.pdf"),
    ("MKT-SW-WB-DIG", "SensWEIGHT Weighbridge Digitalization", "marketing", "SensWEIGHT",
     "weighbridge,digitalization,remote,diagnostics,sensweight",
     "marketing/SensWEIGHT_Weighbridge_Digitalization.pdf"),
    ("MKT-SW-RO", "SensWEIGHT Leaflet RO", "marketing", "SensWEIGHT",
     "sensweight,romania,leaflet,weighing",
     "marketing/SensWEIGHT_Leaflet_A3_RO.pdf"),
    ("MKT-SENSVIBRA", "SensVibra Leaflet A3", "marketing", "SensVibra",
     "sensvibra,vibration,monitoring,industrial,predictive maintenance",
     "marketing/SensVibra_Leaflet_A3_PRINT_READY.pdf"),
    ("PL-SW-SAAS", "SensWEIGHT SaaS Pricing", "price_list", "SensWEIGHT,UCS-CLOUD",
     "pricing,saas,subscription,cloud,sensweight,monthly,annual,basic,advanced,professional,enterprise,59,99,199,299",
     "pricing/SensWEIGHT_SaaS_Pricing.pdf"),
    ("PL-TRUCK-DIG", "Digitalization of Truck Scales Offer", "price_list", "SensWEIGHT,M740-60T",
     "truck scale,digitalization,pricing,offer,load cell",
     "pricing/Digitalizaion of truck scales.pdf"),
    ("PL-LOADCELL-OFFER", "Load Cell Offer Digital Truck Scale", "price_list", "M740-60T,M740D",
     "load cell,offer,truck scale,digital,pricing,m740",
     "pricing/Load cell offer digital truck scale.pdf"),
    ("CERT-OIML-R76", "CE Type Approval OIML R76", "certification", "M740-60T,M740D",
     "ce,oiml,r76,certification,approval,weighing,legal metrology",
     "certificates/CERTIFICATO_APPROVAZIONE_CE_DEL_TIPO_OIMLR76.pdf"),
    ("CERT-OIML-R76-DK", "OIML R76 Certificate DK", "certification", "M740-60T",
     "oiml,r76,certificate,ce,approval,2006",
     "certificates/OIML-Certificate-R76_2006-A-DK2-25.07.pdf"),
    ("CERT-R76-GB", "OIML R76 Certificate GB", "certification", "M740-60T",
     "oiml,r76,gb,certificate,approval",
     "certificates/R76_2006-A-GB1-22.01.pdf"),
    ("CERT-CE-SERIE-W", "CE Type Approval Serie W", "certification", "WDESK-BL,Smart-Digital",
     "ce,serie w,approval,certification,utilcell",
     "certificates/APPROVAZIONE CE DEL TIPO SERIE W.pdf"),
    ("CERT-CE-CLM8", "CE Type Approval CLM8", "certification", "CLM8",
     "ce,clm8,approval,certification,type approval",
     "certificates/APPROVAZIONE CE DEL TIPO - CLM8.pdf"),
    ("CERT-EXPIRY-2028", "Certificate Validity Expires 2028", "certification", "M740-60T,CLM8",
     "certificate,expiry,2028,validity,ce,oiml",
     "certificates/Certificato scad. 2028.pdf"),
    ("VID-ROI-IOT", "ROI of IoT Monitoring", "video", "UCS-CLOUD,SensWEIGHT",
     "roi,iot,monitoring,video,business case,savings",
     "ROI_of_IoT_Monitoring.mp4"),
    ("VID-BIZ-ROI", "UCS Business Model and ROI", "video", "UCS-CLOUD",
     "business model,roi,video,pricing,ucs",
     "pricing/UCS_Business_Model___ROI.mp4"),
    ("VID-DETECTIVE", "Lost Weight Detective Marketing Video", "video", "SensWEIGHT",
     "marketing,video,sensweight,weighing,diagnostics",
     "A_detective_is_after_lost_weig.mp4"),
]

PRODUCTS = [
    ("UCS-X1", "UCS X1 IIoT Module", "Hardware",
     "IIoT gateway: RS-232/RS-485/Ethernet Modbus ASCII to UCS CLOUD via NB-IoT. 8-36V DC 152x94x45mm.",
     "x1,modbus,nb-iot,lpwan,gateway,weighing,indicator,plc", "Modbus,ASCII", "NB-IoT,LPWAN", "Desk/Wall"),
    ("UCS-X1-DIN", "UCS X1 DIN IIoT Module", "Hardware",
     "DIN-rail X1 module. Same connectivity in 54x63x90mm 100g housing.",
     "x1,din,din-rail,modbus,nb-iot,panel,plc", "Modbus,ASCII", "NB-IoT,LPWAN", "DIN Rail"),
    ("UCS-X2", "UCS X2 IIoT Module", "Hardware",
     "Multi-core CPU backup battery improved NB-IoT temp/humidity monitoring. Successor to X1.",
     "x2,battery,nb-iot,weighing,iiot,real-time", "Modbus,ASCII", "NB-IoT,LPWAN", "Desk/Wall"),
    ("UCS-X2-DIN", "UCS X2 DIN IIoT Module", "Hardware",
     "DIN-rail X2 for OEM panel integration with backup battery and enhanced NB-IoT.",
     "x2,din,oem,panel,nb-iot,diagnostics", "Modbus,ASCII", "NB-IoT,LPWAN", "DIN Rail"),
    ("UCS-CLOUD", "UCS CLOUD Service", "Software",
     "Cloud dashboard history email/SMS alarms REST API secure storage 24/7 access.",
     "cloud,dashboard,alarms,sms,email,rest api,saas,subscription", "REST API", "Cloud", "N/A"),
    ("M740D", "Utilcell M740D Digital Load Cell", "Hardware",
     "Digital compression load cell 15-60t OIML R60 C RS-485 IP68 truck scales.",
     "m740d,load cell,digital,15-60t,truck scale,oiml,r60,rs485", "Modbus", "RS-485", "Load cell"),
    ("M740-60T", "Utilcell M740 15-60t", "Hardware",
     "Heavy-capacity load cell for truck scales and weighbridges.",
     "m740,truck scale,weighbridge,15-60t,heavy,load cell", "Modbus", "RS-485", "Load cell"),
    ("WDESK-BL", "WDESK-BL Indicator", "Hardware",
     "Utilcell weighing indicator desk unit.",
     "wdesk,indicator,display,desk,weighing", "Modbus,ASCII", "RS-232,RS-485", "Desk"),
    ("Smart-Digital", "Utilcell Smart-Digital", "Hardware",
     "Smart digital weighing transmitter.",
     "smart digital,transmitter,indicator,utilcell", "Modbus", "RS-485", "Panel"),
    ("CLM8", "Utilcell CLM8", "Hardware",
     "Compact weighing module CE type approved.",
     "clm8,compact,weighing,module,ce", "Modbus", "RS-485", "Compact"),
    ("SensWEIGHT", "SensWEIGHT Solution", "Solution",
     "Remote wireless monitoring for scales weighbridges belt scales silos. European patent IIoT SaaS.",
     "sensweight,weighing,weighbridge,belt scale,silo,remote,diagnostics,iiot,patent", "Modbus", "NB-IoT,LPWAN", "N/A"),
    ("SensSILO", "SensSILO Solution", "Solution",
     "Silo inventory security and structural monitoring 24/7. Works with existing silos.",
     "senssilo,silo,agriculture,grain,inventory,theft,structural,cement", "Modbus", "NB-IoT,LPWAN", "N/A"),
    ("SensVibra", "SensVibra Solution", "Solution",
     "Vibration monitoring for industrial predictive maintenance.",
     "sensvibra,vibration,monitoring,predictive,maintenance", "Modbus", "NB-IoT,LPWAN", "N/A"),
]

PRICES = [
    ("SensWEIGHT", "SW-BASIC-1-9", "59", "EUR", "Basic 1-9 devices/month", "SaaS", "Per device/month. Annual €708 (5% discount). Source: SensWEIGHT_SaaS_Pricing.pdf"),
    ("SensWEIGHT", "SW-ADVANCED-1-9", "99", "EUR", "Advanced 1-9 devices/month", "SaaS", "Per device/month. Annual €1188."),
    ("SensWEIGHT", "SW-PRO-1-9", "199", "EUR", "Professional 1-9 devices/month", "SaaS", "Per device/month. Annual €2388."),
    ("SensWEIGHT", "SW-ENTERPRISE-1-9", "299", "EUR", "Enterprise 1-9 devices/month", "SaaS", "Per device/month. Annual €3588."),
    ("UCS-CLOUD", "UCS-CLOUD-SUB", "Quote on request", "EUR", "Cloud subscription", "Consultation", "Bundled with hardware project scope"),
    ("M740-60T", "M740-TRUCK-OFFER", "See PDF", "EUR", "Truck scale package", "Project", "pricing/Load cell offer digital truck scale.pdf"),
]


def find_source() -> Path:
    for p in SOURCE_CANDIDATES:
        if p.is_dir() and any(p.rglob("*.pdf")):
            return p.resolve()
    raise FileNotFoundError("clients_package folder not found under INFRA651/clients_package/")


def sync_folder(source: Path) -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(source, DEST)


def write_sheets(source: Path) -> None:
    SHEETS.mkdir(parents=True, exist_ok=True)

    with (SHEETS / "Product-Catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "product_name", "category", "description", "keywords", "protocols", "connectivity", "mount_type", "cloud_service", "source"])
        for row in PRODUCTS:
            w.writerow([*row, "UCS CLOUD", "clients_package"])

    with (SHEETS / "Document-Index.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "title", "doc_type", "product_ids", "keywords", "drive_path", "local_path", "format", "source"])
        for doc_id, title, dtype, pids, kw, rel in DOCUMENTS:
            fp = source / rel.replace("/", "\\")
            fmt = "PDF" if rel.lower().endswith(".pdf") else "MP4"
            if not fp.is_file():
                print(f"  warn missing: {rel}")
            w.writerow([
                doc_id, title, dtype, pids, kw,
                f"UCS-Knowledge-Base/clients-package/{rel}",
                f"knowledge-base/clients-package/{rel}",
                fmt, "clients_package",
            ])

    with (SHEETS / "Price-List.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "sku", "list_price_eur", "currency", "price_tier", "pricing_model", "notes", "source"])
        for row in PRICES:
            w.writerow([*row, "clients_package"])

    with (SHEETS / "Applications.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["field", "description", "keywords", "products"])
        w.writerow(["weighing", "Truck/belt/weighbridge scale monitoring", "weighing,truck scale,belt scale,weighbridge,sensweight", "SensWEIGHT,M740-60T"])
        w.writerow(["agriculture", "Silo grain inventory and structural monitoring", "agriculture,silo,grain,farm,senssilo,sensweight", "SensSILO,SensWEIGHT"])
        w.writerow(["construction", "Cement plant silo security and inventory", "cement,plant,silo,security,inventory", "SensSILO,SensWEIGHT"])
        w.writerow(["oem", "OEM digital truck scale load cells", "oem,truck scale,digital,load cell,m740", "M740D,M740-60T,UCS-X2-DIN"])


def main() -> None:
    source = find_source()
    print(f"Source: {source}")
    sync_folder(source)
    write_sheets(source)
    n = len(list(DEST.rglob("*")))
    print(f"Synced {n} files to knowledge-base/clients-package/")
    print(f"Sheets written to {SHEETS}")


if __name__ == "__main__":
    main()
