import argparse, copy, threading, time
from operator import itemgetter
import rtmidi
from rtmidi.midiutil import open_midiinput, open_midioutput

# Constants

SETUP = 0X01000000
SYS_COMMON = 0x02000000
SYS_CTRL = 0x02004000

TMP_PERF_BASE = 0x10000000
PART_OFFSET = 0x2000
ZONE_OFFSET = 0x5000
PART_ADDRESS_BASE = TMP_PERF_BASE + PART_OFFSET
ZONE_ADDRESS_BASE = TMP_PERF_BASE + ZONE_OFFSET
PATCH_ADDRESS_BASE = 0x11000000
SOUND_DEMO_SWITCH = 0x0F002000 # set to 0x00 for turning off, 0x01 1st layer etc.

RQ1 = 0x11
DT1 = 0x12
IDENTITY_REQUEST = [0xF0, 0x7E, 0x10, 0x06, 0x01, 0xF7]
IDENTITY_REPLY_START = [0xF0, 0x7E, 0x10, 0x06, 0x02, 0x41] 

MODEL_IDS = {
    "GK": '0000003C',  # Model IDs 
    "GP": '0000003D' 
}
MODEL_ID_AUX = '00000028' # GO keyboards respond also to this address. Corresponding parameter address map is not well known

KEYS = ['C-1', 'C#-1', 'D-1', 'Eb-1', 'E-1', 'F-1', 'F#-1', 'G-1', 'G#-1', 'A-1', 'Bb-1', 'B-1', 'C0', 'C#0','D0', 'Eb0', 'E0', 'F0', 'F#0', 'G0', 'G#0', 'A0', 'Bb0', 'B0', 'C1', 'C#1', 'D1', 'Eb1', 'E1', 'F1', 'F#1', 'G1', 'G#1', 'A1', 'Bb1', 'B1', 'C2', 'C#2', 'D2', 'Eb2', 'E2', 'F2', 'F#2', 'G2', 'G#2', 'A2', 'Bb2', 'B2', 'C3', 'C#3', 'D3', 'Eb3', 'E3', 'F3', 'F#3', 'G 3', 'G#3', 'A3', 'Bb3', 'B3', 'C4', 'C#4', 'D4', 'Eb4', 'E4', 'F4', 'F#4', 'G4', 'G#4', 'A4', 'Bb4', 'B4', 'C5', 'C#5', 'D5', 'Eb5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5', 'Bb5', 'B5', 'C6', 'C#6', 'D6', 'Eb6', 'E6', 'F6', 'F#6', 'G6', 'G#6', 'A6', 'Bb6', 'B6', 'C7', 'C#7', 'D7', 'Eb7', 'E7', 'F7', 'F#7', 'G7', 'G#7', 'A7', 'Bb7', 'B7', 'C8', 'C#8', 'D8', 'Eb8', 'E8', 'F8', 'F#8', 'G8', 'G#8', 'A8', 'Bb8', 'B8', 'C9', 'C#9', 'D9', 'Eb9', 'E9', 'F9', 'F#9', 'G9']
PATCH_CATEGORIES = ["DRM","PNO","EP","KEY","BEL","MLT","ORG", "ACD","HRM", "AGT", "EGT", "DGT", "BS", "SBS", "STR", "ORC", "HIT", "WND","FLT", "BRS", "SBR", "SAX", "HLD", "SLD", "TEK", "PLS", "FX", "SYN", "BPD", "SPD", "VOX", "PLK", "ETH", "FRT","PRC", "SFX", "BTS", "DRM", "CMB", "SMP"]

LOOPMIX_STYLES = ['Trance','Funk','House','Drum N Bass','Neo HipHop','Pop','Bright Rock','Trap Step','Future Bass','Trad HipHop','EDM','R&B', 'Reggaeton', 'Cumbia', 'ColombianPop', 'Bossa Lounge', 'Arrocha', 'Drum N Bossa', 'Bahia Mix', 'Power Rock', 'Classic Rock', 'J-Pop']
LOOPMIX_KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
TEMPO_DOWN_ADDR = 0x01000503
TEMPO_UP_ADDR = 0x01000504

SETUP_MODEL = [ 
		{ "addr": 0x0000,	"size": 1, "data_width": 3,	"ofs": 0,	"init": 0,	"min": 0,	"max": 4,	"name": "SoundMode" },
		{ "addr": 0x0001,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 85,	"min": 0,	"max": 127,	"name": "PerformBankSelMSB(CC#0)" },
		{ "addr": 0x0002,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 64,	"min": 0,	"max": 127,	"name": "PerformBankSelLSB(CC#32)" },
		{ "addr": 0x0003,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "PerformProgramNum(PC)" },
		{ "addr": 0x0004,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 87,	"min": 0,	"max": 127,	"name": "KbdPatchBankSelMSB(CC#0)" },
		{ "addr": 0x0005,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 73,	"min": 0,	"max": 127,	"name": "KbdPatchBankSelLSB(CC#32)" },
		{ "addr": 0x0006,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "KbdPatchProgramNum(PC)" },
		{ "addr": 0x0007,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 86,	"min": 0,	"max": 127,	"name": "RhyPatchBankSelMSB(CC#0)" },
		{ "addr": 0x0008,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 65,	"min": 0,	"max": 127,	"name": "RhyPatchBankSelLSB(CC#32)" },
		{ "addr": 0x0009,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "RhyPatchProgramNum(PC)" },
		{ "addr": 0x000A,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "MFX1Sw" },
		{ "addr": 0x000B,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "MFX2Sw" },
		{ "addr": 0x000C,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "MFX3Sw" },
		{ "addr": 0x000D,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ChorusSw" },
		{ "addr": 0x000E,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ReverbSw" },
		{ "addr": 0x000F,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0010,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0011,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0012,	"size": 1, "data_width": 4,	"ofs": 64,	"init": 0,	"min": -5,	"max": 6,	"name": "TransposeValue" },
		{ "addr": 0x0013,	"size": 1, "data_width": 3,	"ofs": 64,	"init": 0,	"min": -3,	"max": 3,	"name": "OctaveShift" },
		{ "addr": 0x0014,	"size": 1, "data_width": 3,	"ofs": 0,	"init": 0,	"min": 0,	"max": 3,	"name": "DBeamSelect" },
		{ "addr": 0x0015,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 0,	"min": 0,	"max": 2,	"name": "KnobSelect" },
		{ "addr": 0x0016,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0017,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 5,	"min": 0,	"max": 8,	"name": "Arp/PtnGrid" },
		{ "addr": 0x0018,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 5,	"min": 0,	"max": 9,	"name": "Arp/PtnDuration" },
		{ "addr": 0x0019,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "ArpeggioSw" },
		{ "addr": 0x001A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "ArpeggioStyle" },
		{ "addr": 0x001C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 2,	"min": 0,	"max": 11,	"name": "ArpeggioMotif" },
		{ "addr": 0x001D,	"size": 1, "data_width": 3,	"ofs": 64,	"init": 0,	"min": -3,	"max": 3,	"name": "ArpeggioOctaveRange" },
		{ "addr": 0x001E,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "ArpeggioHold" },
		{ "addr": 0x001F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 100,"min": 0,	"max": 100,	"name": "ArpeggioAccentRate" },
		{ "addr": 0x0020,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "ArpeggioVelocity" },
		{ "addr": 0x0021,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "DrumPtnSw" },
		{ "addr": 0x0022,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0023,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 255,	"name": "DrumPtnStyle" },
		{ "addr": 0x0025,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0026,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 29,	"name": "DrumPtnGroupNum" },
		{ "addr": 0x0027,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 100,"min": 0,	"max": 100,	"name": "DrumPtnAccentRate" },
		{ "addr": 0x0028,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 1,	"max": 127,	"name": "DrumPtnVelocity" },
		{ "addr": 0x0029,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "ChordSw" },
		{ "addr": 0x002A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002B,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 16,	"name": "ChordForm" },
		{ "addr": 0x002C,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002D,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002E,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002F,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0030,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0031,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "RolledChord" },
		{ "addr": 0x0032,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 0,	"min": 0,	"max": 2,	"name": "RolledChordType" },
		{ "addr": 0x0033,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 32,	"name": "ArpeggioStep" }
	]

SYS_COMMON_MODEL = [ 
		{ "addr": 0x0000,	"size": 4, "data_width": 4,	"ofs": 1024,"init": 0,	"min": -1000,"max": 1000,"name": "MasterTune" },
		{ "addr": 0x0004,	"size": 1, "data_width": 6,	"ofs": 64,	"init": 0,	"min": -24,	"max": 24,	"name": "MasterKeyShift" },
		{ "addr": 0x0005,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 0,	"max": 127,	"name": "MasterLevel" },
		{ "addr": 0x0006,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ScaleTuneSw" },
		{ "addr": 0x0007,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "PatchRemain" },
		{ "addr": 0x0008,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "Mix/Parallel" },
		{ "addr": 0x0009,	"size": 1, "data_width": 5,	"ofs": 0,	"init": 15,	"min": 0,	"max": 16,	"name": "PerformCtrlChannel" },
		{ "addr": 0x000A,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 15,	"name": "KbdPatchRx/TxChannel" },
		{ "addr": 0x000B,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x000C,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(C)" },
		{ "addr": 0x000D,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(C#)" },
		{ "addr": 0x000E,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(D)" },
		{ "addr": 0x000F,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(D#)" },
		{ "addr": 0x0010,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(E)" },
		{ "addr": 0x0011,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(F)" },
		{ "addr": 0x0012,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(F#)" },
		{ "addr": 0x0013,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(G)" },
		{ "addr": 0x0014,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(G#)" },
		{ "addr": 0x0015,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(A)" },
		{ "addr": 0x0016,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(A#)" },
		{ "addr": 0x0017,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PatchScaleTune(B)" },
		{ "addr": 0x0018,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 97,	"name": "SystemCtrl1Source" },
		{ "addr": 0x0019,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 97,	"name": "SystemCtrl2Source" },
		{ "addr": 0x001A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 97,	"name": "SystemCtrl3Source" },
		{ "addr": 0x001B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 97,	"name": "SystemCtrl4Source" },
		{ "addr": 0x001C,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ReceiveProgramChange" },
		{ "addr": 0x001D,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ReceiveBankSel" }
	]

SYS_CTRL_MODEL = [ 
		{ "addr": 0x0000,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "TransmitProgramChange" },
		{ "addr": 0x0001,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "TransmitBankSel" },
		{ "addr": 0x0002,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "KbdVelocity" },
		{ "addr": 0x0003,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 2,	"min": 1,	"max": 3,	"name": "KbdVelocityCurve" },
		{ "addr": 0x0004,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0005,	"size": 1, "data_width": 3,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "HoldPedalPolarity" },
		{ "addr": 0x0006,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "ContinuousHoldPedal" },
		{ "addr": 0x0007,	"size": 1, "data_width": 5,	"ofs": 0,	"init": 4,	"min": 0,	"max": 24,	"name": "PedalAssign" },
		{ "addr": 0x0008,	"size": 1, "data_width": 3,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "Pedal1Polarity" },
		{ "addr": 0x0009,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 5,	"min": 1,	"max": 10,	"name": "BeamSens" },
		{ "addr": 0x000A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 19,	"name": "BeamAssign" },
		{ "addr": 0x000B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "BeamRangeLower" },
		{ "addr": 0x000C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 0,	"max": 127,	"name": "BeamRangeUpper" },
		{ "addr": 0x000D,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 15,	"name": "(reserve)" },
		{ "addr": 0x000E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 100,"min": 1,	"max": 127,	"name": "(reserve)" },
		{ "addr": 0x000F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "(reserve)" },
		{ "addr": 0x0010,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 104,	"name": "Knob1Assign" },
		{ "addr": 0x0011,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 104,	"name": "Knob2Assign" },
		{ "addr": 0x0012,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 104,	"name": "Knob3Assign" },
		{ "addr": 0x0013,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 104,	"name": "Knob4Assign" },
		{ "addr": 0x0014,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0015,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0016,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0017,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0018,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0019,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0020,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0021,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0022,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0023,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0024,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0025,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0026,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0027,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0028,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0029,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x002F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0030,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0031,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0032,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0033,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0034,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0035,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0036,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0037,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0038,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0039,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x003F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0040,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0041,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0042,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0043,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0044,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0045,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0046,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0047,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0048,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0049,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x004A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x004B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x004C,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x004D,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" }
	]

ZONE_MODEL = [
            { "addr": 0x0000,	"size": 1, "data_width": 3,	"ofs": 64,	"init": 0,	"min": -3,	"max": 3,	"name": "ZoneOctaveShift" },
            { "addr": 0x0001,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "ZoneSw" },
            { "addr": 0x0002,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0003,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 128,"min": 128,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0005,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "(reserve)" },
            { "addr": 0x0006,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 128,"min": 128,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0008,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 128,"min": 128,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x000A,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 128,"min": 128,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x000C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "KbdRangeLower" },
            { "addr": 0x000D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 0,	"max": 127,	"name": "KbdRangeUpper" },
            { "addr": 0x000E,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x000F,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0010,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0011,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0012,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0013,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0014,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0015,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0016,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0017,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0018,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x0019,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
            { "addr": 0x001A,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" }
        ]

PART_MODEL = [ 
		{ "addr": 0x0000,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 15,	"name": "ReceiveChannel" },
		{ "addr": 0x0001,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "ReceiveSw" },
		{ "addr": 0x0002,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0003,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 1,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0004,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 87,	"min": 0,	"max": 127,	"name": "PatchBankSelMSB(CC#0)" },
		{ "addr": 0x0005,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 64,	"min": 0,	"max": 127,	"name": "PatchBankSelLSB(CC#32)" },
		{ "addr": 0x0006,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "PatchProgramNum(PC)" },
		{ "addr": 0x0007,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 100,"min": 0,	"max": 127,	"name": "PartLevel(CC#7)" },
		{ "addr": 0x0008,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 64,	"min": 0,	"max": 127,	"name": "PartPan(CC#10)" },
		{ "addr": 0x0009,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -48,	"max": 48,	"name": "PartCoarseTune(RPN#2)" },
		{ "addr": 0x000A,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -50,	"max": 50,	"name": "PartFineTune(RPN#1)" },
		{ "addr": 0x000B,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 2,	"min": 0,	"max": 2,	"name": "PartMono/Poly(MONO ON/POLY ON)" },
		{ "addr": 0x000C,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 2,	"min": 0,	"max": 2,	"name": "PartLegatoSw(CC#68)" },
		{ "addr": 0x000D,	"size": 1, "data_width": 5,	"ofs": 0,	"init": 25,	"min": 0,	"max": 25,	"name": "PartPitchBendRange(RPN#0)" },
		{ "addr": 0x000E,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 2,	"min": 0,	"max": 2,	"name": "PartPortamentoSw(CC#65)" },
		{ "addr": 0x000F,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 128,"min": 0,	"max": 128,	"name": "PartPortamentoTime(CC#5)" },
		{ "addr": 0x0011,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartCutoffOffset(CC#74)" },
		{ "addr": 0x0012,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartResonanceOffset(CC#71)" },
		{ "addr": 0x0013,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartAttackTimeOffset(CC#73)" },
		{ "addr": 0x0014,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartReleaseTimeOffset(CC#72)" },
		{ "addr": 0x0015,	"size": 1, "data_width": 3,	"ofs": 64,	"init": 0,	"min": -3,	"max": 3,	"name": "PartOctaveShift" },
		{ "addr": 0x0016,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "PartVelocitySensOffset" },
		{ "addr": 0x0017,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0018,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0019,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001A,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001B,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "MuteSw" },
		{ "addr": 0x001C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 0,	"max": 127,	"name": "PartDrySendLevel" },
		{ "addr": 0x001D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "PartChorusSendLevel(CC#93)" },
		{ "addr": 0x001E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "PartReverbSendLevel(CC#91)" },
		{ "addr": 0x001F,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 1,	"min": 0,	"max": 13,	"name": "PartOutputAssign" },
		{ "addr": 0x0020,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 0,	"min": 0,	"max": 2,	"name": "PartOutputMFXSelect" },
		{ "addr": 0x0021,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartDecayTimeOffset(CC#75)" },
		{ "addr": 0x0022,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartVibratoRate(CC#76)" },
		{ "addr": 0x0023,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartVibratoDepth(CC#77)" },
		{ "addr": 0x0024,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartVibratoDelay(CC#78)" },
		{ "addr": 0x0025,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(C)" },
		{ "addr": 0x0026,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(C#)" },
		{ "addr": 0x0027,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(D)" },
		{ "addr": 0x0028,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(D#)" },
		{ "addr": 0x0029,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(E)" },
		{ "addr": 0x002A,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(F)" },
		{ "addr": 0x002B,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(F#)" },
		{ "addr": 0x002C,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(G)" },
		{ "addr": 0x002D,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(G#)" },
		{ "addr": 0x002E,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(A)" },
		{ "addr": 0x002F,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(A#)" },
		{ "addr": 0x0030,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -64,	"max": 63,	"name": "PartScaleTune(B)" }
	]

PATCH_COMMON_MODEL = [ 
		{ "addr": 0x0000,	"size": 12, "data_width": 7,"ofs": 0,	"init": "INIT PATCH  ",	"min": 32,	"max": 127,	"name": "PatchName" },
		{ "addr": 0x000C,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "PatchCategory" },
		{ "addr": 0x000D,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x000E,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 127,"min": 0,	"max": 127,	"name": "PatchLevel" },
		{ "addr": 0x000F,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 64,	"min": 0,	"max": 127,	"name": "PatchPan" },
		{ "addr": 0x0010,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PatchPriority" },
		{ "addr": 0x0011,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -48,	"max": 48,	"name": "PatchCoarseTune" },
		{ "addr": 0x0012,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -50,	"max": 50,	"name": "PatchFineTune" },
		{ "addr": 0x0013,	"size": 1, "data_width": 3,	"ofs": 64,	"init": 0,	"min": -3,	"max": 3,	"name": "OctaveShift" },
		{ "addr": 0x0014,	"size": 1, "data_width": 2,	"ofs": 0,	"init": 0,	"min": 0,	"max": 3,	"name": "StretchTuneDepth" },
		{ "addr": 0x0015,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 127,	"name": "AnalogFeel" },
		{ "addr": 0x0016,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 1,	"min": 0,	"max": 1,	"name": "Mono/Poly" },
		{ "addr": 0x0017,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "LegatoSw" },
		{ "addr": 0x0018,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "LegatoRetrigger" },
		{ "addr": 0x0019,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PortamentoSw" },
		{ "addr": 0x001A,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PortamentoMode" },
		{ "addr": 0x001B,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PortamentoType" },
		{ "addr": 0x001C,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PortamentoStart" },
		{ "addr": 0x001D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 20,	"min": 0,	"max": 127,	"name": "PortamentoTime" },
		{ "addr": 0x001E,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x001F,	"size": 2, "data_width": 4,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0021,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 0,	"name": "(reserve)" },
		{ "addr": 0x0022,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "CutoffOffset" },
		{ "addr": 0x0023,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "ResonanceOffset" },
		{ "addr": 0x0024,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "AttackTimeOffset" },
		{ "addr": 0x0025,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "ReleaseTimeOffset" },
		{ "addr": 0x0026,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "VelocitySensOffset" },
		{ "addr": 0x0027,	"size": 1, "data_width": 4,	"ofs": 0,	"init": 13,	"min": 0,	"max": 13,	"name": "PatchOutputAssign" },
		{ "addr": 0x0028,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "TMTCtrlSw" },
		{ "addr": 0x0029,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 2,	"min": 0,	"max": 48,	"name": "PitchBendRangeUp" },
		{ "addr": 0x002A,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 2,	"min": 0,	"max": 48,	"name": "PitchBendRangeDown" },
		{ "addr": 0x002B,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 109,	"name": "MatrixCtrl1Source" },
		{ "addr": 0x002C,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl1Destination1" },
		{ "addr": 0x002D,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl1SourceSens1" },
		{ "addr": 0x002E,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl1Destination2" },
		{ "addr": 0x002F,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl1Name2" },
		{ "addr": 0x0030,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl1Destination3" },
		{ "addr": 0x0031,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl1Sens3" },
		{ "addr": 0x0032,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl1Destination4" },
		{ "addr": 0x0033,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl1Sens4" },
		{ "addr": 0x0034,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 109,	"name": "MatrixCtrl2Source" },
		{ "addr": 0x0035,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl2Destination1" },
		{ "addr": 0x0036,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl2Sens1" },
		{ "addr": 0x0037,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl2Destination2" },
		{ "addr": 0x0038,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl2Sens2" },
		{ "addr": 0x0039,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl2Destination3" },
		{ "addr": 0x003A,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl2Sens3" },
		{ "addr": 0x003B,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl2Destination4" },
		{ "addr": 0x003C,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl2Sens4" },
		{ "addr": 0x003D,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 109,	"name": "MatrixCtrl3Source" },
		{ "addr": 0x003E,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl3Destination1" },
		{ "addr": 0x003F,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl3Sens1" },
		{ "addr": 0x0040,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl3Destination2" },
		{ "addr": 0x0041,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl3Sens2" },
		{ "addr": 0x0042,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl3Destination3" },
		{ "addr": 0x0043,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl3Sens3" },
		{ "addr": 0x0044,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl3Destination4" },
		{ "addr": 0x0045,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl3Sens4" },
		{ "addr": 0x0046,	"size": 1, "data_width": 7,	"ofs": 0,	"init": 0,	"min": 0,	"max": 109,	"name": "MatrixCtrl4Source" },
		{ "addr": 0x0047,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl4Destination1" },
		{ "addr": 0x0048,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl4Sens1" },
		{ "addr": 0x0049,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl4Destination2" },
		{ "addr": 0x004A,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl4Sens2" },
		{ "addr": 0x004B,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl4Destination3" },
		{ "addr": 0x004C,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl4Sens3" },
		{ "addr": 0x004D,	"size": 1, "data_width": 6,	"ofs": 0,	"init": 0,	"min": 0,	"max": 33,	"name": "MatrixCtrl4Destination4" },
		{ "addr": 0x004E,	"size": 1, "data_width": 7,	"ofs": 64,	"init": 0,	"min": -63,	"max": 63,	"name": "MatrixCtrl4Sens4" },
		{ "addr": 0x004F,	"size": 1, "data_width": 1,	"ofs": 0,	"init": 0,	"min": 0,	"max": 1,	"name": "PartModulationSw" }
	]

class MidiManager:
    def __init__(self, port):
        self.input_device_name = port
        self.output_device_name = port
        self.midi_in = None
        self.midi_out = None
    def __enter__(self):
        self.open_devices()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_devices()    
    def open_devices(self):
        try: # if MIDI port is not specified, try to open first available one
            if self.input_device_name is None:
                self.midi_in, self.input_device_name = open_midiinput(0)
            else:
                self.midi_in, self.input_device_name = open_midiinput(self.input_device_name) 
            self.midi_in.ignore_types(sysex=False)
            if self.output_device_name is None:
                self.midi_out, self.output_device_name = open_midioutput(0)
            else:
                self.midi_out, self.output_device_name = open_midioutput(self.output_device_name)
            return True
        except Exception as e:
            print(f"Error opening MIDI devices: {e}")
            return False
    def close_devices(self):
      if self.midi_in:
        self.midi_in.close_port()
      if self.midi_out:
        self.midi_out.close_port()
    def send_cc(self, channel, cc_number, value):
        """Sends a Control Change (CC) message."""
        message = [
            0xB0 + (channel - 1),  # Control Change (0xB0) on the specified channel
            cc_number,             # The CC number
            value                  # The CC value
        ]
        self.midi_out.send_message(message)
    def send_rpn(self, channel, param_msb, param_lsb, data_msb, data_lsb):
        """Sends a Registered Parameter Number (RPN) command."""
        # RPN Select
        self.send_cc(channel, 0x65, param_msb)    # RPN MSB
        self.send_cc(channel, 0x64, param_lsb)    # RPN LSB 
        # Data Entry
        self.send_cc(channel, 0x06, data_msb)   # Data MSB
        self.send_cc(channel, 0x26, data_lsb)   # Data LSB
        # Null function 
        self.send_cc(channel, 0x65, 0x7F)  # RPN Select (MSB = 127)
        self.send_cc(channel, 0x64, 0x7F)  # RPN LSB (LSB = 127) 

    def send_rpnf(self,channel, parameter_number, value):
        """Send RPN number (0-16383) with value (0-16383)"""
        # Calculate parameter number bytes (MSB, LSB)
        param_msb = (parameter_number >> 7) & 0x7F
        param_lsb = parameter_number & 0x7F
        # Calculate value bytes (MSB, LSB)
        value_msb = (value >> 7) & 0x7F
        value_lsb = value & 0x7F
        self.send_rpn(channel,param_msb,param_lsb,value_msb,value_lsb)

    def send_nrpn(self, ch, nrpn_msb, nrpn_lsb, data_msb, data_lsb):
        """Sends an NRPN (Non-Registered Parameter Number) command."""
        #self.midi_out.send_message([0xB0 + (ch - 1), 0x63, nrpn_msb])
        #self.midi_out.send_message([0xB0 + (ch - 1), 0x62, nrpn_lsb])
        #self.midi_out.send_message([0xB0 + (ch - 1), 0x06, data_msb])
        #self.midi_out.send_message([0xB0 + (ch - 1), 0x26, data_lsb])
        self.send_cc(ch, 0x63, nrpn_msb)  # NRPN MSB
        self.send_cc(ch, 0x62, nrpn_lsb)  # NRPN LSB
        self.send_cc(ch, 0x06, data_msb)  # Data MSB
        self.send_cc(ch, 0x26, data_lsb)  # Data LSB
        # Null function 
        # self.send_cc(channel, 0x65, 0x7F)  # RPN Select (MSB = 127)
        # self.send_cc(channel, 0x64, 0x7F)  # RPN LSB (LSB = 127) 

    def send_nrpnf(self,channel, parameter_number, value):
        """Send NRPN number (0-16383) with value (0-16383)"""
        param_msb = (parameter_number >> 7) & 0x7F
        param_lsb = parameter_number & 0x7F
        value_msb = (value >> 7) & 0x7F
        value_lsb = value & 0x7F
        self.send_nrpn(channel,param_msb,param_lsb,value_msb,value_lsb)
  

def convert_address_to_bytes(address):
    """Converts an integer address into a list of 4 bytes.
    Args:
        address: The integer address value.
    Returns:
        A list of 4 bytes representing the address.
    """
    return [(address >> (8 * i)) & 0xFF for i in range(3, -1, -1)]

def split_hex_string(hex_string):
    """Converts a hexadecimal string into a list of integer bytes."""
    return [int(hex_string[i:i+2], 16) for i in range(0, len(hex_string), 2)]

def checksum(address, data):
    return (128 - (sum(address) + sum(data)) % 128) & 0x7F

def slice_to_7bit(x):
    """Slices a 32-bit value into four 7-bit MIDI data bytes.
    Args:
        x: The 32-bit integer value to be sliced.
    Returns:
        An integer where each byte represents a 7-bit MIDI byte.
    """
    group1 = (x & 0x0fe00000) << 3 
    group2 = (x & 0x001fc000) << 2 
    group3 = (x & 0x00003f80) << 1 
    group4 = (x & 0x0000007f)  
    return group1 | group2 | group3 | group4

def reassemble_from_7bit(x):
    """Reassembles a 32-bit value from four 7-bit MIDI data bytes.
    Args:
        x:  An integer containing the four 7-bit bytes in a single value.
    Returns:
        The original 32-bit integer value.
    """
    group1 = (x & 0x7f000000) >> 3  
    group2 = (x & 0x007f0000) >> 2
    group3 = (x & 0x00007f00) >> 1
    group4 = (x & 0x0000007f) 
    return group1 | group2 | group3 | group4 

def validate_patch(patch_str):
    """Validates a patch string in the format MSB,LSB,PC with range checks."""
    try:
        msb, lsb, pc = map(int, patch_str.split(','))
        if not (0 <= msb <= 127 and 0 <= lsb <= 127 and 1 <= pc <= 128):
            raise argparse.ArgumentTypeError("MSB/LSB must be 0-127, PC must be 1-128")
        return msb, lsb, pc
    except ValueError:
        raise argparse.ArgumentTypeError("Patch must be in format: MSB,LSB,PC") 


def construct_rq1_command(model_id, address, size):
    """Constructs a Roland RQ1 (Read Request) SysEx command. """
    model_id_bytes = split_hex_string(model_id)
    address_bytes = convert_address_to_bytes(address)
    encoded_size_bytes = list(slice_to_7bit(size).to_bytes(4, 'big')) 
    checksum_value = checksum(address_bytes, encoded_size_bytes) 
    message = [
        0xF0,      # Start of SysEx
        0x41, 0x10,  # This is Roland
        *model_id_bytes, 
        RQ1,               # RQ1 command type
        *address_bytes, 
        *encoded_size_bytes, 
        checksum_value, 
        0xF7               # End of SysEx
    ]
    return message

def construct_dt1_command(model_id, address, data_bytes): 
    """Constructs a Roland DT1 (Data Transmission) SysEx command."""
    model_id_bytes = split_hex_string(model_id)
    address_bytes = convert_address_to_bytes(address)
    checksum_value = checksum(address_bytes, data_bytes)  
    message = [
        0xF0,      # Start of SysEx
        0x41, 0x10,  # This is Roland
        *model_id_bytes, 
        DT1,               # DT1 command type
        *address_bytes, 
        *data_bytes,
        checksum_value, 
        0xF7               # End of SysEx
    ]
    return message

def calculate_part_address(part_num):
    return PART_ADDRESS_BASE + (part_num - 1) * 0x100

def calculate_zone_address(zone_num):
    return ZONE_ADDRESS_BASE + (zone_num - 1) * 0x100

def calculate_patch_address(part_num):
    return slice_to_7bit(reassemble_from_7bit(PATCH_ADDRESS_BASE ) + (part_num - 1) * reassemble_from_7bit(0x00200000))

def get_zone_config(zone_num,midi_manager,model_id):
    zone_address = calculate_zone_address(zone_num)
    zone_config = get_params(ZONE_MODEL,zone_address,model_id,midi_manager)
    return zone_config

def get_part_config(part_num,midi_manager,model_id):
    part_address = calculate_part_address(part_num)
    part_config = get_params(PART_MODEL,part_address,model_id,midi_manager)
    return part_config

def get_patch_common_config(part_num,midi_manager,model_id):
    patch_address = calculate_patch_address(part_num)
    patch_config = get_params(PATCH_COMMON_MODEL,patch_address,model_id,midi_manager)
    return patch_config

#def extract_nibbles(encoded_value, num_nibbles):
#     return [(encoded_value >> (4 * i)) & 0xf for i in range(num_nibbles - 1, -1, -1)]

def read_map_data(start_addr,size,model_id,midi_manager):
    rq1_command = construct_rq1_command(model_id, start_addr, size)
    data_ready_event = threading.Event()
    received_message = []
    def data_callback(event,data):
        message,_ = event
        # check if the received DT1 message address matches the sent RQ1 address
        # TODO: implement more complete checks
        if rq1_command[8:12] == message[8:12]:
            data.extend(message)
            data_ready_event.set()  # Signal completion
            midi_manager.midi_in.cancel_callback()  # Cleanup
    midi_manager.midi_in.set_callback(data_callback,data=received_message)
    midi_manager.midi_out.send_message(rq1_command)
    data_ready_event.wait()
    received_data = received_message[12:-2]
    assert len(received_data) == size
    return received_data

def write_map_data(start_addr,data,model_id,midi_manager):
    dt1_command = construct_dt1_command(model_id,start_addr,data)
    midi_manager.midi_out.send_message(dt1_command)

def get_params(data_model,start_addr,model_id,midi_manager):
    """ sends RQ1 and awaits response """
    size = sum(i["size"] for i in data_model)
    received_data = read_map_data(start_addr,size,model_id,midi_manager)
    params = bytes_to_params(received_data,data_model)
    return params

def bytes_to_params(data_bytes,data_model):
    """Tranforms raw binary data into a structured representation based on a provided model."""
    model_size = sum(i["size"] for i in data_model)
    assert len(data_bytes) == model_size
    params = copy.deepcopy(data_model)
    params_by_addr = {reassemble_from_7bit(param["addr"]): param for param in params}
    for addr,param in params_by_addr.items():
        size = param["size"]
        if size == 1:
            value = data_bytes[addr]
            value -= param["ofs"]
            param["value"] = value
        elif size == 2:
            byte1, byte2 = data_bytes[addr:addr+2]
            value = (byte1 & 0x0F) << 4 | (byte2 & 0x0F)
            value -= param["ofs"]
            param["value"] = value
        elif size == 4:
            byte1, byte2, byte3, byte4 = data_bytes[addr:addr+4]
            value = (byte1 & 0x0F) << 12 | (byte2 & 0x0F) << 8 | (byte3 & 0x0F) << 4 | (byte4 & 0x0F)
            value -= param["ofs"]
            param["value"] = value
        elif size == 12: # this is ASCII string
            value = bytes(data_bytes[addr:addr+12]).decode('ascii')
            param["value"] = value
        else: # shouldn't happen
            raise ValueError(f"Unhandled data type - {size} bytes")
    return params    
    
def params_to_bytes(params):
    """Packs model parameters with their values into a list of bytes according to a specified model."""
    model_size = sum(param["size"] for param in params)
    data_bytes = model_size * [None]
    params_by_addr = {reassemble_from_7bit(param["addr"]): param for param in params}
    for addr,param in params_by_addr.items():
        size = param["size"]
        data_width = param["data_width"]
        value = param.get("value", param["init"])
        if size == 1:
            encoded_value = value + param["ofs"]
            data_bytes[addr] = encoded_value
        elif size == 2 and data_width == 4:
            # 4-bit value spread across two bytes
            encoded_value = value + param["ofs"]
            byte1 = encoded_value & 0x0F # lsb
            byte2 = (encoded_value >> 4) & 0x0F # msb
            data_bytes[addr:addr+2] = [byte2,byte1]
            # or data_bytes[addr:addr+4] = extract_nibbles(encoded_value, 2)
        elif size == 4 and data_width == 4:
            encoded_value = value + param["ofs"]
            byte1 = encoded_value & 0x0F
            byte2 = (encoded_value >> 4) & 0x0F
            byte3 = (encoded_value >> 8) & 0x0F
            byte4 = (encoded_value >> 12) & 0x0F
            data_bytes[addr:addr+4] = [byte4,byte3,byte2,byte1]
            # or data_bytes[addr:addr+4] = extract_nibbles(encoded_value, 4)
        elif size == 12 and data_width == 7: # this is ASCII string
            data_bytes[addr:addr+12] = list(bytes(value,'ascii'))
        else: # shouldn't happen
            raise ValueError(f"Unhandled data type - {size} bytes")
    assert all(i != None for i in data_bytes)    # check that we have all the data
    return data_bytes

def part_set(args,midi_manager):
    model_id = MODEL_IDS[args.model] if args.model else None 
    print(f"Configuring part {args.part} on model {args.model}: Patch({args.patch}), Channel({args.channel}), Level({args.level}), Octave Shift({args.octave_shift}), Model ID: {model_id}")
    part_params = get_part_config(args.part,midi_manager,model_id)

    params_by_name = {param["name"]: param for param in part_params if param["name"] != "(reserve)" }
    # Update zone configuration based on arguments (using KEYS for mapping)

    if args.channel is not None:
        params_by_name["ReceiveChannel"]["value"] = args.channel - 1
    if args.octave_shift is not None:
        params_by_name["PartOctaveShift"]["value"] = args.octave_shift
    if args.level is not None:
        params_by_name["PartLevel(CC#7)"]["value"] = args.level
    if args.patch is not None:
        params_by_name["PatchBankSelMSB(CC#0)"]["value"] = args.patch[0]
        params_by_name["PatchBankSelLSB(CC#32)"]["value"] = args.patch[1]
        params_by_name["PatchProgramNum(PC)"]["value"] = args.patch[2] - 1

    # Encode and send the message 
    address = calculate_part_address(args.part)
    data_bytes = params_to_bytes(part_params)
    sysex_message = construct_dt1_command(model_id, address, data_bytes)
    midi_manager.midi_out.send_message(sysex_message)

def part_get(args,midi_manager):
    part_config = get_part_config(args.part,midi_manager,MODEL_IDS[args.model])
    param_vals = {param["name"]:param["value"] for param in part_config if param["name"] != "(reserve)"}
    print(param_vals)
    for k,v in param_vals.items():
        print(f"{k}: {v}")

def part_preview(args,midi_manager):
    model_id = MODEL_IDS[args.model]
    start_demo_cmd = construct_dt1_command(model_id, SOUND_DEMO_SWITCH, [args.part_num])
    stop_demo_cmd = construct_dt1_command(model_id, SOUND_DEMO_SWITCH, [0])

    part_params = get_part_config(args.part_num,midi_manager,model_id)
    part_params_by_name = {param["name"]: param for param in part_params }
    patch_common_params = get_patch_common_config(args.part_num,midi_manager,model_id)
    patch_common_params_by_name = {param["name"]: param for param in patch_common_params }

    msb = part_params_by_name["PatchBankSelMSB(CC#0)"]["value"]
    lsb = part_params_by_name["PatchBankSelLSB(CC#32)"]["value"]
    pc = part_params_by_name["PatchProgramNum(PC)"]["value"] + 1
    patch_name = patch_common_params_by_name["PatchName"]["value"]
    patch_category = patch_common_params_by_name["PatchCategory"]["value"]
        
    print(f"Playing part {args.part_num}: patch name: '{patch_name.strip()}' ({msb},{lsb},{pc}), category: {PATCH_CATEGORIES[patch_category]}")
    midi_manager.midi_out.send_message(start_demo_cmd)
    time.sleep(args.duration)
    midi_manager.midi_out.send_message(stop_demo_cmd)

def set_zone(args,midi_manager):
    
    model_id = MODEL_IDS[args.model] if args.model else None 
    #print(f"Configuring zone {args.zone} on model {args.model}: Octave Shift({args.octave_shift}), Low Key({args.low_key}), High Key({args.high_key}), Status({args.on if args.on else 'off'}), Model ID: {model_id}")

    zone_params = get_zone_config(args.zone,midi_manager,model_id)
    zone_config = {param["name"]: param for param in zone_params if param["name"] != "(reserve)" }
    # Update zone configuration based on arguments (using KEYS for mapping)
    if args.octave_shift is not None:
        zone_config["ZoneOctaveShift"]["value"] = args.octave_shift
    if (args.on or args.off): # on or off was explicitly specified
        zone_config["ZoneSw"]["value"] = int(args.on)
    if args.low_key is not None:
        zone_config["KbdRangeLower"]["value"] = KEYS.index(args.low_key)  
    if args.high_key is not None:
        zone_config["KbdRangeUpper"]["value"] = KEYS.index(args.high_key)

    # Encode and send the message 
    address = calculate_zone_address(args.zone)
    #print(f"zone address: {address.to_bytes(4,'big').hex(' ')}")
    data_bytes = params_to_bytes(zone_params)
    sysex_message = construct_dt1_command(model_id, address, data_bytes)
    #print("Sending SysEx Command:", bytes(sysex_message).hex(' '))
    midi_manager.midi_out.send_message(sysex_message)

def zone_show(args,midi_manager):
    if not args.zones:
        zone_numbers = range(1,17)
    else:
        zone_numbers = set(args.zones)
    attrs = ['ZoneSw', 'ZoneOctaveShift', 'KbdRangeLower','KbdRangeUpper']
    attribute_extractor = itemgetter(*attrs)
    value_transformations = {
        'KbdRangeLower': lambda x: KEYS[x],
        'KbdRangeUpper': lambda x: KEYS[x],
        'ZoneSw': lambda x: 'on' if x else 'off'
    }
    output_row_format ="{:>20}" * (len(attrs) + 1)
    print(output_row_format.format("Zone number", *attrs))
    for i in zone_numbers:
        zone_config =  get_zone_config(i,midi_manager,MODEL_IDS[args.model])
        raw_param_values = {param["name"]:param["value"] for param in zone_config}
        transformed_param_values = transform_values(raw_param_values,value_transformations)
        #print(row_format.format(i,*selector(tr_values)))
        print(output_row_format.format(i, *attribute_extractor(transformed_param_values))) 


def part_show(args,midi_manager):
    if not args.parts:
        parts = range(1,17)
    else:
        parts = set(args.parts)
    attrs = ['ReceiveChannel', 'PatchBankSelMSB(CC#0)', 'PatchBankSelLSB(CC#32)','PatchProgramNum(PC)',
             'PartLevel(CC#7)','PartOctaveShift']
    selector = itemgetter(*attrs)
    value_transformations = {
        'ReceiveChannel': lambda x: x+1,
        'PatchProgramNum(PC)': lambda x: x+1,
        'ReceiveSw': lambda x: 'on' if x else 'off'
    }
    row_format ="{:>24}" * (len(attrs) + 1)
    print(row_format.format("Part number", *attrs))
    for i in parts:
        part_config =  get_part_config(i,midi_manager,MODEL_IDS[args.model])
        param_vals = {param["name"]:param["value"] for param in part_config}
        tr_values = transform_values(param_vals,value_transformations)
        print(row_format.format(i,*selector(tr_values)))

def sys_show(args,midi_manager):
    setup_config = get_params(SETUP_MODEL,SETUP,MODEL_IDS[args.model],midi_manager)
    sys_common_config = get_params(SYS_COMMON_MODEL,SYS_COMMON,MODEL_IDS[args.model],midi_manager)
    sys_ctrl_config = get_params(SYS_CTRL_MODEL,SYS_CTRL,MODEL_IDS[args.model],midi_manager)
    for block in (setup_config,sys_common_config,sys_ctrl_config):
        param_vals = {param["name"]:param["value"] for param in block if param["name"] != "(reserve)"}
        for k,v in param_vals.items():
            print(f"{k}: {v}")
    #print(setup_config)
    #print(sys_common_config)
    #print(sys_ctrl_config)
   

def autodetect_model(midi_port,midi_manager):
    """ sends Idenyity request and awaits response """
    data_ready_event = threading.Event()
    received_message = []
    def data_callback(event,data):
        message,_ = event
        # check if the received message is Identity Reply
        # TODO: implement more complete checks
        if message[0:6] == IDENTITY_REPLY_START:
            data.extend(message)
            data_ready_event.set()  # Signal completion
            midi_manager.midi_in.cancel_callback()  # Cleanup
    midi_manager.midi_in.set_callback(data_callback,data=received_message)
    midi_manager.midi_out.send_message(IDENTITY_REQUEST)
    data_ready_event.wait()
    #print(bytes(received_message).hex(' '))
    if received_message[6] == 0x3c:
        model = 'GK'
    elif received_message[6] == 0x3d:
        model = 'GP'
    else:
        raise Exception(f"Unsupported model")
    return model

def loopmix_select(args,midi_manager):
    print(f"Selected {LOOPMIX_STYLES[args.style-1]}")
    midi_manager.send_nrpn(16,0,0,0,args.style-1)

def loopmix_exit(args,midi_manager):
    # stop playing
    midi_manager.send_nrpn(16,0,3,0,0)
    # exit loop mixing mode
    model_id = MODEL_IDS[args.model]
    sysex_message = construct_dt1_command(model_id, 0x01000019, [0])
    midi_manager.midi_out.send_message(sysex_message)

def loopmix_play(args,midi_manager):
    loopmix_part = args.loopmix_part
    pattern = args.pattern
    midi_manager.send_nrpn(16,0,1,loopmix_part-1,pattern-1)

def loopmix_key(args,midi_manager):
    key_index = LOOPMIX_KEYS.index(args.key)
    midi_manager.send_nrpn(16,0,2,0,key_index)

def loopmix_tempo(args,midi_manager):
    byte1, byte2 = read_map_data(0x01000108,2,MODEL_ID_AUX,midi_manager)
    tempo = (byte1 << 7) | byte2 # same as; (128 * byte1) + byte2
    dt = args.tempo_delta
    if dt is None or dt == 0:
        print(f"Loop mix tempo: {tempo} bpm")
    else:
        addr = TEMPO_UP_ADDR if args.tempo_delta > 0 else TEMPO_DOWN_ADDR
        for _ in range(abs(dt)):
            write_map_data(addr,[0],MODEL_ID_AUX,midi_manager)
            time.sleep(0.04)
        byte1, byte2 = read_map_data(0x01000108,2,MODEL_ID_AUX,midi_manager)
        new_tempo = (byte1 << 7) | byte2 # same as; (128 * byte1) + byte2
        print(f"Tempo changed from {tempo} to {new_tempo} bpm.")

def loopmix_stop(args,midi_manager):
    if args.loopmix_part is None: # stop playing all loopmix parts
        midi_manager.send_nrpn(16,0,3,0,0)
    else:
        midi_manager.send_nrpn(16,0,3,0,args.loopmix_part)

def transform_values(row, transformations):
    """Applies transformations to a data row.""" 
    return {k : transformations.get(k, lambda x: x)(v) for k,v in row.items() }


def main():
    # Main parser 
    parser = argparse.ArgumentParser(description="%(prog)s - GO:KEYS and GO:PIANO Sound Management Tool")
#    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
    parser.add_argument('-p', '--port', required=False, help="MIDI port (default: first available)") 
    parser.add_argument('--model', choices=MODEL_IDS.keys(), help="Select model (GK/GP, auto-detect if omitted)")

    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    # sys command
    sys_parser = subparsers.add_parser('sys',help="system data")
    sys_subparsers = sys_parser.add_subparsers(title="subcommands", dest="subcommand", help='additional help')
    # 'get' subcommand within 'sys'
    sys_show_parser = sys_subparsers.add_parser('show', help="Get setup & system properties")
    sys_show_parser.set_defaults(func=sys_show)

    # parts command 
    part_parser = subparsers.add_parser('part', help="Manage configuration of parts")
    part_subparsers = part_parser.add_subparsers(title="subcommands", dest="subcommand", help='additional help')

    #  'set' subcommand within 'part'
    part_set_parser = part_subparsers.add_parser('set', help="Set part properties")
    part_set_parser.add_argument('part', type=int, choices=range(1, 17), help="Part number",metavar='PART_NUM')
    part_set_parser.add_argument('--patch', type=validate_patch, help="Patch specified as MSB,LSB,PC")
    part_set_parser.add_argument('--channel', type=int, help="MIDI receive channel", choices=range(1, 17), metavar='CHAN')
    part_set_parser.add_argument('--level', type=int, help="Part level (volume)")
    part_set_parser.add_argument('--octave-shift', type=int, choices=range(-3,4), help="Octave shift for the part")
    part_set_parser.set_defaults(func=part_set) 

    # 'get' subcommand within 'part'
    part_get_parser = part_subparsers.add_parser('get', help="Get zone properties")
    part_get_parser.add_argument('part', type=int, choices=range(1, 17), help="Part number",metavar='PART_NUM')
    part_get_parser.set_defaults(func=part_get)

    # 'show' subcommand within 'part'
    part_show_parser = part_subparsers.add_parser('show', help="Show zone properties")
    part_show_parser.add_argument('parts', type=int, choices=range(1, 17), nargs='*',help="Part number",metavar='ZONE_NUM')
    part_show_parser.set_defaults(func=part_show)

       # 'preview" subcommand within 'part'
    part_preview_parser = part_subparsers.add_parser('preview', help="Play a part's demo sound")
    part_preview_parser.add_argument('part_num', type=int, choices=range(1, 17), help="Part number",metavar='PART_NUM')
    part_preview_parser.add_argument("--duration", type=int, default=5, help="Set preview length in seconds (default: 5)") 
    part_preview_parser.set_defaults(func=part_preview)

    # zone command 
    zone_parser = subparsers.add_parser('zone', help="Manage configuration of zones")
    zone_subparsers = zone_parser.add_subparsers(title="subcommands", dest="subcommand", help='additional help')

    # 'set' subcommand within 'zone'
    zone_set_parser = zone_subparsers.add_parser('set', help="Set zone properties")
    zone_set_parser.add_argument('zone', type=int, choices=range(1, 17), help="Zone number",metavar='ZONE_NUM')   
    zone_set_parser.add_argument('--octave-shift', type=int, choices=range(-3,4), help="Octave shift for the zone")
    zone_onoff_group = zone_set_parser.add_mutually_exclusive_group(required=False)
    zone_onoff_group.add_argument('--on', action='store_true', help="Enable the zone")
    zone_onoff_group.add_argument('--off', action='store_true', help="Disable the zone")
    zone_set_parser.add_argument('--low-key', choices=KEYS, help="Zone's lower key", metavar='KEY')
    zone_set_parser.add_argument('--high-key', choices=KEYS, help="Zone's upper key", metavar='KEY')
    zone_set_parser.set_defaults(func=set_zone)

    # 'show' subcommand within 'zone'
    zone_show_parser = zone_subparsers.add_parser('show', help="Show zone properties")
    zone_show_parser.add_argument('zones', type=int, choices=range(1, 17), nargs='*',help="Zone number",metavar='ZONE_NUM')
    zone_show_parser.set_defaults(func=zone_show)
    
     # loopmix command 
    loopmix_parser = subparsers.add_parser('loopmix', help="Manage loop mixes")
    loopmix_subparsers = loopmix_parser.add_subparsers(title="subcommands", dest="subcommand", help='additional help')

    # loopmix select
    loopmix_select_parser = loopmix_subparsers.add_parser('select', help="select loop style")
    loopmix_select_parser.add_argument('style', type=int, choices=range(1,23), help = "loop mix style", metavar='STYLE')
    loopmix_select_parser.set_defaults(func=loopmix_select)

    # loopmix play
    loopmix_play_parser = loopmix_subparsers.add_parser('play', help="play loopmix part")
    loopmix_play_parser.add_argument('loopmix_part',type=int, choices=range(1,6), help="loop mix part(1-5)")
    loopmix_play_parser.add_argument('pattern', type=int, choices=range(1,12),help='loop pattern variation')
    loopmix_play_parser.set_defaults(func=loopmix_play)

    # loopmix stop
    loopmix_stop_parser = loopmix_subparsers.add_parser('stop', help="stop playing loopmix part")
    loopmix_stop_parser.add_argument('loopmix_part',type=int, choices=range(1,6), nargs='?', help="loop mix part(1-5)")
    loopmix_stop_parser.set_defaults(func=loopmix_stop)

    # loopmix tempo
    loopmix_tempo_parser = loopmix_subparsers.add_parser('tempo', help="loopmix tempo")
    loopmix_tempo_parser.add_argument('tempo_delta', type=int, help="loop mix tempo", nargs='?')
    loopmix_tempo_parser.set_defaults(func=loopmix_tempo)

    # loopmix key
    loopmix_key_parser = loopmix_subparsers.add_parser('key', help="loopmix key")
    loopmix_key_parser.add_argument('key', choices=LOOPMIX_KEYS, help="loop mix key", metavar="KEY")
    loopmix_key_parser.set_defaults(func=loopmix_key)

    # loopmix exit
    loopmix_exit_parser = loopmix_subparsers.add_parser('exit', help="exit loop mixing mode")
    loopmix_exit_parser.set_defaults(func=loopmix_exit)

    # Parse the arguments 
    args = parser.parse_args()

   #lets open the midi device
    #midi_manager = MidiManager(args.port)
    with MidiManager(args.port) as midi_manager:
        # Model selection/detection logic
        if args.model is None:
            args.model = autodetect_model(args.port,midi_manager)
        if 'subcommand' in args and args.subcommand:
            args.func(args,midi_manager)
        else:
            parser.print_help()
    
#    midi_manager.close_devices()

if __name__ == "__main__":
    main()

