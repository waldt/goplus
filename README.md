# GO:Plus

## Expanding the Sonic Capabilities of Roland GO:PIANO and GO:KEYS
GO:Plus gives you access to a wider range of sounds and performance features normally not accessible on your GO keyboard. This utility leverages MIDI protocol to expose these hidden capabilities.

Empirical evidence suggests a near-identical synth engine to the Roland Juno-DS (excluding sample-based sounds), with lineage tracing back to Fantom and XV series synths.

## Features
* **Enable Splits and Layers:** Combine multiple sounds to create richer performances.
* **Access Hidden Patches:** Discover a vast library of additional instrument sounds normally not available on your keyboard.
* **Explore Loop Mixing (even on GO:PIANO!)**: Experiment with fun beat combinations and rhythmic patterns. Customize your loops further by changing instruments!

## Roadmap
* Easier selection of sound patches.
* Better command structure for smoother workflow.
* Saving customized sound settings to keyboard memory. 
* Unlocking a capable effects module.

## Important Notes

* **GO:Plus is experimental:** It's an unofficial tool and not supported by Roland. Use at your own risk.
* **Designed for exploration:** This tool is best for discovering new possibilities, not for live performance reliability.
* **Experiment. Discover. Share.**
* **A vision for the future:** An interactive app on a tablet or phone would provide a more performance-friendly interface. Community collaboration is welcome on this idea!

## Terminology

* **Sounds in GO:KEYS and GO:PIANO:** While the manuals refer to individual sounds as "tones," these are functionally equivalent to what other Roland synths call "patches." They're the playable units of sound.
* **Patches vs. Tones:** Patches can be made up of up to four sounds (referred to as "tones" on other synthesizers, like the Juno-DS), interacting in complex ways. These individual "tones" cannot be played by themselves.
* **Layering and Splits:** Roland synthesizers do not  use explicit "layer" terminology internally. To achieve sound layering or splits, you set up a "performance" in which you configure multiple "parts" with different sounds and keyboard "zones" as active key ranges. To create a split with piano on the right and strings on the left, enable two parts, assign the desired patches, and set their zones to the appropriate key ranges.
* **Performances:** A "performance" allows you to assign a patch to each of its 16 parts, enabling you to play up to 16 sounds simultaneously. For example, a "performance" could combine layered piano and strings across the full keyboard with a bass patch on the lower octaves.
* **Consistent Terminology:** For clarity, this project will use the Juno-DS terminology (performances, patches, tones, etc.) as it's the closest and more capable relative to GO keyboards.

## Installation

1. **Have Python 3 installed**
2. **Download `gotool.py`:** Get the latest version from this GitHub repository.
3. **Install dependency:** 
   `pip install python-rtmidi`
4. **Connect your GO: device:** Ensure it's powered on and connected to your computer via USB or Bluetooth MIDI (compatibility varies by OS).


## Basic Usage

* Basic Command:  `goplus [command] [options]`
* List Available Commands:  `goplus --help`
* Each subcommand has a dedicated help section 


##  Commands

- **Example 1: Create a Layered Piano/Strings Sound:**
   - `python goplus.py part set 1 --patch 87,64,4`: Select a piano sound
   - `python goplus.py part set 2 --patch 87,67,27`: Select a strings sound
   - `python goplus.py zone set 1 --on`: Piano across the keyboard
   - `python goplus.py zone set 2 --on`: Strings layered on top

- **Example 2: Set Up a Keyboard Split:**
  - `python goplus.py part set 1 --patch 87,73,37`: Select a bass sound
  - `python goplus.py part set 2 --patch 87,64,9`: Select a piano sound
  - `python goplus.py zone set 1 --high-key B3 --octave-shift -1`: Bass on lower keys
  - `python goplus.py zone set 2 --low-key C4`: Piano on upper keys

- **Additional Examples:**
  - **Exploring patches:** `python goplus.py part preview 1`: Play a demo of part 1 sound
  - **Listing configurations:**
    - `python goplus.py  part show` :  Show status of all parts
    - `python goplus.py  zone show 2 5 8` :  Show info on zones 2, 5, and 8   

**Important Notes:**

- **Patch numbers** can be found in Rolands's *Parameter Guide* for Juno DS or [here](GO-sounds.md).
- **Case sensitivity:** Key notes (e.g., C4, G#5) must be provided in the correct case.
- **Value Ranges:**
  - MSB, LSB: 0-127
  - PC: 1-128
  - Level: 0-127
  - Octave Shift: -3 to +3
- Layer 1 is always active, even if set to `off`

## Contributing

We welcome contributions to improve GO:Plus. Please check out our [`CONTRIBUTING.md`](CONTRIBUTING) file for guidelines.

## License

This project is licensed under the Apache License, Version 2.0 - see the [`LICENSE`](LICENSE) file for details.
