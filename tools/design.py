"""回路の定義（部品・ネット）。回路図 (gen_sch.py) と基板 (gen_pcb.py) の唯一の情報源。

各部品: ref, lib(シンボル), value, fp(フットプリント), at(回路図上の位置 mm), pins{ピン番号: ネット名 / None=未接続}
"""

PROJECT = "claude-pico2"
TITLE = "RP2350A Pico 互換基板"
REV = "0.1"

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"

PARTS = []


def part(ref, lib, value, fp, at, pins, **extra):
    PARTS.append(dict(ref=ref, lib=lib, value=value, fp=fp, at=at, pins={str(k): v for k, v in pins.items()}, extra=extra))


def R(ref, value, at, a, b, **kw):
    part(ref, "Device:R", value, R0402, at, {1: a, 2: b}, **kw)


def C(ref, value, at, a, b="GND", fp=C0402, **kw):
    part(ref, "Device:C", value, fp, at, {1: a, 2: b}, **kw)


# ---------------------------------------------------------------- MCU
u1 = {}
for n in (1, 11, 20, 30, 38, 45):
    u1[n] = "+3V3"  # IOVDD
for n in (6, 23, 39):
    u1[n] = "+1V1"  # DVDD
gpio_pins = {
    0: 2, 1: 3, 2: 4, 3: 5, 4: 7, 5: 8, 6: 9, 7: 10, 8: 12, 9: 13, 10: 14, 11: 15,
    12: 16, 13: 17, 14: 18, 15: 19, 16: 27, 17: 28, 18: 29, 19: 31, 20: 32, 21: 33,
    22: 34, 23: 35, 24: 36, 25: 37, 26: 40, 27: 41, 28: 42, 29: 43,
}
for g, n in gpio_pins.items():
    u1[n] = "GPIO%d" % g
u1.update({
    21: "XIN", 22: "XOUT", 24: "SWCLK", 25: "SWDIO", 26: "RUN",
    44: "ADC_VREF",  # ADC_AVDD (Pico と同じく ADC_VREF をそのまま供給)
    46: "VREG_AVDD", 47: "GND", 48: "VREG_LX", 49: "+3V3", 50: "+1V1",
    51: "USB_DM", 52: "USB_DP", 53: "+3V3", 54: "+3V3",
    55: "QSPI_SD3", 56: "QSPI_SCLK", 57: "QSPI_SD0", 58: "QSPI_SD2", 59: "QSPI_SD1", 60: "QSPI_SS",
    61: "GND",
})
part("U1", "MCU_RaspberryPi:RP2350A", "RP2350A", "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm",
     (203.2, 152.4), u1, labels_only=True, mpn="RP2350A")

# ---------------------------------------------------------------- QSPI Flash + BOOTSEL
part("U2", "Memory_Flash:W25Q32JVZP", "W25Q32RVXHJQ", "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm",
     (127.0, 152.4),
     {1: "QSPI_SS", 2: "QSPI_SD1", 3: "QSPI_SD2", 4: "GND", 5: "QSPI_SD0", 6: "QSPI_SCLK", 7: "QSPI_SD3", 8: "+3V3", 9: "GND"},
     mpn="W25Q32RVXHJQ")
C("C20", "100n", (147.32, 142.24), "+3V3")
R("R5", "1k", (106.68, 190.5), "QSPI_SS", "BOOTSEL")
part("SW1", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_SPST_B3U-1000P", (132.08, 195.58),
     {1: "BOOTSEL", 2: "GND"}, mpn="B3U-1000P")

# ---------------------------------------------------------------- USB Type-C
part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     (45.72, 60.96),
     {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
      "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
      "A5": "CC1", "B5": "CC2", "A6": "USB_CONN_DP", "B6": "USB_CONN_DP", "A7": "USB_CONN_DM", "B7": "USB_CONN_DM",
      "A8": None, "B8": None},
     mpn="TYPE-C-31-M-12")
R("R1", "27", (88.9, 104.14), "USB_CONN_DP", "USB_DP")
R("R2", "27", (99.06, 104.14), "USB_CONN_DM", "USB_DM")
R("R3", "5.1k", (88.9, 60.96), "CC1", "GND")
R("R4", "5.1k", (99.06, 60.96), "CC2", "GND")

# ---------------------------------------------------------------- 3.3V 昇降圧電源
part("D1", "Device:D_Schottky", "MBR120VLSFT1G", "Diode_SMD:D_SOD-123F", (127.0, 35.56),
     {1: "VSYS", 2: "VBUS"}, mpn="MBR120VLSFT1G")
C("C1", "10u", (139.7, 60.96), "VSYS", fp=C0603)
R("R10", "100k", (160.02, 60.96), "VSYS", "3V3_EN")
part("U3", "Regulator_Switching:TPS63001", "TPS63001", "Package_SON:Texas_DRC0010J", (185.42, 50.8),
     {1: "+3V3", 2: "BB_L2", 3: "GND", 4: "BB_L1", 5: "VSYS", 6: "3V3_EN", 7: "GPIO23", 8: "VSYS", 9: "GND", 10: "+3V3", 11: "GND"},
     mpn="TPS63001DRCR")
part("L1", "Device:L", "2.2u", "Inductor_SMD:L_Murata_DFE201610P", (165.1, 83.82), {1: "BB_L1", 2: "BB_L2"},
     mpn="DFE201612E-2R2M")
C("C3", "22u", (210.82, 60.96), "+3V3", fp=C0603)

# ---------------------------------------------------------------- 電源監視・LED・ADC 基準
R("R12", "5.6k", (254.0, 60.96), "VBUS", "GPIO24")
R("R13", "10k", (254.0, 99.06), "GPIO24", "GND")
R("R14", "200k", (271.78, 60.96), "VSYS", "GPIO29")
R("R15", "100k", (271.78, 99.06), "GPIO29", "GND")
R("R9", "470", (317.5, 60.96), "GPIO25", "LED_A")
part("D2", "Device:LED", "Green", "LED_SMD:LED_0603_1608Metric", (335.28, 60.96), {1: "GND", 2: "LED_A"})
R("R8", "200", (358.14, 60.96), "+3V3", "ADC_VREF")
C("C19", "2.2u", (368.3, 83.82), "ADC_VREF")
C("C18", "100n", (378.46, 83.82), "ADC_VREF")

# ---------------------------------------------------------------- 水晶
part("Y1", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (63.5, 241.3),
     {1: "XIN", 2: "GND", 3: "XOUT_R", 4: "GND"}, mpn="ABM8-272-T3")
C("C21", "15p", (40.64, 254.0), "XIN")
C("C22", "15p", (86.36, 254.0), "XOUT_R")
R("R6", "1k", (99.06, 254.0), "XOUT_R", "XOUT")

# ---------------------------------------------------------------- コア電源 (RP2350 内蔵 SMPS)
part("L2", "Device:L", "3.3u", "Inductor_SMD:L_Murata_DFE201610P", (121.92, 254.0), {1: "+1V1", 2: "VREG_LX"},
     mpn="AOTA-B201610S3R3-101-T")
C("C5", "4.7u", (132.08, 254.0), "+3V3")
C("C6", "4.7u", (142.24, 254.0), "+1V1")
R("R7", "33", (152.4, 254.0), "+3V3", "VREG_AVDD")
C("C7", "4.7u", (165.1, 254.0), "VREG_AVDD")

# ---------------------------------------------------------------- デカップリング
for i, ref in enumerate(("C8", "C9", "C10", "C11", "C13")):  # IOVDD
    C(ref, "100n", (180.34 + 7.62 * i, 254.0), "+3V3")
for i, ref in enumerate(("C14", "C16")):  # DVDD
    C(ref, "100n", (231.14 + 7.62 * i, 254.0), "+1V1")

# ---------------------------------------------------------------- Pico 40 ピン / SWD / 取付穴
left = ["GPIO0", "GPIO1", "GND", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GND", "GPIO6", "GPIO7",
        "GPIO8", "GPIO9", "GND", "GPIO10", "GPIO11", "GPIO12", "GPIO13", "GND", "GPIO14", "GPIO15"]
right = ["GPIO16", "GPIO17", "GND", "GPIO18", "GPIO19", "GPIO20", "GPIO21", "GND", "GPIO22", "RUN",
         "GPIO26", "GPIO27", "GND", "GPIO28", "ADC_VREF", "+3V3", "3V3_EN", "GND", "VSYS", "VBUS"]
PICO_PINS = left + right  # index 0 = ピン 1
part("J2", "Connector_Generic:Conn_02x20_Counter_Clockwise", "Pico 40pin", "claude_pico:PicoEdge_40",
     (317.5, 152.4), {i + 1: n for i, n in enumerate(PICO_PINS)}, labels_only=True)
part("J3", "Connector_Generic:Conn_01x03", "SWD", "claude_pico:PicoDebug_3", (368.3, 190.5),
     {1: "SWCLK", 2: "GND", 3: "SWDIO"}, labels_only=True)
part("H1", "Mechanical:MountingHole", "M2", "MountingHole:MountingHole_2.1mm", (368.3, 215.9), {})
part("H2", "Mechanical:MountingHole", "M2", "MountingHole:MountingHole_2.1mm", (383.54, 215.9), {})

# ---------------------------------------------------------------- ERC 用の電源フラグ
for i, net in enumerate(("GND", "VBUS", "VSYS", "+1V1", "ADC_VREF", "VREG_AVDD")):
    part("#FLG0%d" % (i + 1), "power:PWR_FLAG", "PWR_FLAG", "", (289.56 + 12.7 * i, 231.14), {1: net}, labels_only=(net != "GND"))

# 回路図に置く見出し (x, y, text)
NOTES = [
    (25.4, 22.86, "USB Type-C"),
    (119.38, 22.86, "3.3V 昇降圧電源 (VBUS → VSYS → +3V3)"),
    (246.38, 22.86, "VBUS 検出 (GPIO24) / VSYS 測定 (GPIO29) / LED (GPIO25) / ADC 基準"),
    (104.14, 124.46, "QSPI Flash / BOOTSEL"),
    (152.4, 101.6, "MCU"),
    (299.72, 119.38, "Pico 互換 40 ピン / SWD"),
    (30.48, 226.06, "12MHz 水晶"),
    (114.3, 226.06, "コア電源 1.1V (内蔵 SMPS)"),
    (175.26, 226.06, "デカップリング (IOVDD / DVDD)"),
]


def nets():
    """ネット名 -> [(ref, pin)]"""
    out = {}
    for p in PARTS:
        if p["ref"].startswith("#"):
            continue
        for num, net in p["pins"].items():
            if net:
                out.setdefault(net, []).append((p["ref"], num))
    return out


if __name__ == "__main__":
    for net, pins in sorted(nets().items()):
        print("%-12s %s" % (net, " ".join("%s.%s" % rp for rp in pins)))
    print(len([p for p in PARTS if not p["ref"].startswith("#")]), "parts")
