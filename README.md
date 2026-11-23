# Print Doctor by [MeshDab](https://meshdab.com/?utm_source=github&utm_medium=readme&utm_campaign=print-doctor)

AI print troubleshooting for OrcaSlicer.

Print Doctor is a plugin for OrcaSlicer 2.5.1 or newer. It adds a chat panel: you describe a print problem (stringing, warping, supports that will not come off, a rough top surface...) or attach a photo or a sliced file, the AI reads your current Orca settings and the model on the plate, and proposes changes to the process and filament presets. Nothing changes until you press Apply, and every applied change can be undone.

> **Status: beta.** The code is covered by automated tests that run outside OrcaSlicer. Testing inside OrcaSlicer is still in progress, so expect rough edges.

## What it can do

- **Chat with attachments:** photos of the print, and sliced files (`.gcode`, `.bgcode`, `.gcode.3mf`/`.3mf`). From a sliced file the AI reads print time and filament, slicer warnings, the settings actually used, per-layer times and flow per feature.
- **Looks at your model:** cross-sections at any height (hole diameters, thinnest walls), overhang and bridge areas, plate contact area, mesh problems (open edges, flipped normals, floating objects). Object sizes account for scale, rotation and mirror.
- **Checks your presets:** what differs from the stock preset and what is still unsaved, plate type against the filament's plate temperatures, nozzle against the profile, layer height and line widths against the nozzle.
- **Calibration helper:** tells you which Orca calibration test to run, how to read it, and turns your reading into the value to enter.
- **Figures and 3D view:** the AI can draw figures in the chat (sections, overhangs, layer times, flow) and open its own 3D window, where it can ask you to click the spot you mean, or take a picture of the model to look at it. Orca's own 3D view is never touched.
- **Proposals you control:** every change is shown with old value, new value and reason; nothing changes until you press Apply, every applied change can be undone, and the chat keeps a history of what was proposed, applied or blocked.
- **Language:** the panel is in 23 languages and follows the language chosen in OrcaSlicer's preferences. You can write to the AI in any language.

## Install

Requirements: OrcaSlicer 2.5.1 or newer. Nothing else to install.

1. Download `print_doctor.py` from the [Releases page](https://github.com/MarcoPiazza83/Print-Doctor/releases) (under **Assets** of the newest release).
2. In OrcaSlicer: **File → Plugins → Install local plugin**, pick the file, activate it and accept the permissions (network and threads).
3. Select **Print Doctor** in the Plugins window and press **Run**: the panel opens on the right.
4. Open the settings (gear icon) and connect an AI service.

To update, install the new `print_doctor.py` the same way. Settings and keys live in the plugin's storage folder, not in the file; if they are gone after an update, connect the AI service again.

## AI services

| Service | How you connect |
|---|---|
| ChatGPT | "Continue with ChatGPT": uses your own ChatGPT plan through OpenAI's official sign-in for open-source apps (preview) |
| Claude | Your own Claude plan (Pro, Max, Team, Enterprise) through Claude Code, a free program from Anthropic (Claude Desktop alone is not enough): see [Claude with your Claude plan](#claude-with-your-claude-plan) |
| OpenRouter | Browser sign-in, or an API key |
| Anthropic, OpenAI, Google Gemini | Your own API key |
| Ollama, LM Studio | Local models, no key |
| Any OpenAI-compatible server | Base URL and key |

Requests go straight from your computer to the service you choose. Keys and tokens are stored only on your computer, in the plugin's settings file.

No ChatGPT or Claude plan? A Google Gemini key is free: create it in a minute at [Google AI Studio](https://aistudio.google.com/apikey), no credit card needed (daily limits apply).

## Claude with your Claude plan

Print Doctor can use your Claude subscription through **Claude Code**, Anthropic's own program, installed on your computer and signed in with your account. Print Doctor never sees your sign-in.

> **The Claude desktop app is not enough.** Claude Desktop (the app with the chat window) and Claude Code (a command-line program) are two different programs. Print Doctor talks only to Claude Code. You sign in to both with the same Claude account, and you do not need to uninstall or change Claude Desktop.

**Which plans work:** Claude Pro, Max, Team or Enterprise. The free Claude plan does not include Claude Code: with a free plan, use another service (a Google Gemini key is free).

**Requirements:** macOS 13 or newer, Windows 10 (version 1809) or newer, or a recent Linux (Ubuntu 20.04+, Debian 10+). No administrator rights needed.

### Step 1: open a terminal

- **macOS:** press `Cmd` + `Space`, type `Terminal`, press Enter.
- **Windows:** right-click the Start button and choose **Terminal** or **Windows PowerShell** (not "Command Prompt", the commands below are for PowerShell).
- **Linux:** open your Terminal app (often `Ctrl` + `Alt` + `T`).

### Step 2: install Claude Code

Copy the line for your system, paste it in the terminal and press Enter. This is Anthropic's official installer ([setup page](https://code.claude.com/docs/en/setup)).

- **macOS and Linux:**
  ```
  curl -fsSL https://claude.ai/install.sh | bash
  ```
- **Windows (PowerShell):**
  ```
  irm https://claude.ai/install.ps1 | iex
  ```

Wait until it says it has finished. Other ways to install (Homebrew, WinGet, npm) are on the setup page; any of them works with Print Doctor.

### Step 3: check that it is installed

**Close the terminal and open a new one** (the new program is only seen by terminals opened after the install), then type:

```
claude --version
```

You should see a version number, for example `2.1.211 (Claude Code)`.

If you get *command not found* (macOS, Linux) or *not recognized* (Windows), the install folder is not in your PATH yet: see Anthropic's [installation troubleshooting page](https://code.claude.com/docs/en/troubleshoot-install). You can also skip the PATH and give Print Doctor the full path in step 5.

### Step 4: sign in (once)

In the terminal type:

```
claude
```

and press Enter. The first time, Claude Code asks you to sign in:

1. Choose to sign in with your **Claude account** (subscription), not with an API key.
2. Your browser opens: sign in with the same account you use on claude.ai or in Claude Desktop, and allow access.
3. Back in the terminal, Claude Code may ask a few first-run questions (theme, trusting the folder): the defaults are fine.

When you see Claude Code's prompt, you are signed in. Type `/exit` and press Enter (or just close the terminal). You never need to open the terminal again for Print Doctor.

### Step 5: connect Print Doctor

1. If OrcaSlicer was open during the install, **close it and open it again**, so it sees the new program.
2. Open Print Doctor, press the gear icon and choose **Claude** as the service.
3. The panel should show *Claude Code found* and the program's path.
   - Shows *Claude Code was not found*? Find the path in a terminal:
     - macOS, Linux: `which claude` (usually `/Users/<you>/.local/bin/claude` on macOS, `/home/<you>/.local/bin/claude` on Linux)
     - Windows: `where.exe claude` (usually `C:\Users\<you>\.local\bin\claude.exe`; if it lists several, copy the one ending in `.exe`)

     and paste it into **Claude Code program**.
4. Optional: choose a model (`opus`, `sonnet`, `haiku`). Leave it empty to use Claude Code's default.

### Step 6: use it

Write your problem in the chat and send it. The first time, OrcaSlicer asks whether Print Doctor may start a program (the `claude` command): answer **Yes**. It does not ask again.

From now on you just use the chat: Print Doctor starts Claude Code by itself in the background, there is no terminal or window to keep open. Claude Code updates itself automatically.

### How it works

Print Doctor starts your own, unmodified Claude Code and gives it Print Doctor's tools through a connection that never leaves your computer (127.0.0.1, protected by a random key). Claude Code runs with all its own tools turned off, so it can only read your Orca settings and propose changes through Print Doctor, with the same safety rules as every other service. Print Doctor never reads, stores or sends your Claude credentials.

### Good to know

- Usage counts toward your Claude plan's limits, like using Claude Code yourself, and is shared with your chats on claude.ai and Claude Desktop. Anthropic's terms apply.
- If the environment variable `ANTHROPIC_API_KEY` is set on your computer, Claude Code uses that key instead of your plan, and the API bills it.
- Error *Claude Code is not signed in*: repeat step 4.
- Error *usage limit reached*: your plan's limit for now is used up; it resets after a few hours.
- Something odd? In a terminal, `claude doctor` checks the installation without starting a chat.
- To remove Claude Code later, follow the uninstall section of Anthropic's [setup page](https://code.claude.com/docs/en/setup).
- If Anthropic changes how Claude Code works with subscriptions, this option may stop working. The Anthropic option with an API key, and the other services, keep working.

## Privacy

There is no Print Doctor server. What the AI service receives is what it needs to answer: your messages, the photos and sliced files you attach, the settings it reads, measurements of the objects on the plate and, when it asks for one, a picture of the plugin's 3D window. That service's own privacy terms apply. With Claude, requests go from Claude Code on your computer to Anthropic. With Ollama or LM Studio everything stays on your computer.

## Safety rules

The plugin enforces these in code, twice: when the AI proposes a change and again before it is applied.

- Printer settings are never changed.
- Custom G-code, post-processing scripts, material data, temperature ranges and chamber heating are never changed.
- Only settings on an explicit allow-list can be changed, each with a type and a range. Anything else is explained to you as a manual step.
- Nozzle temperature stays inside the filament's own range; plate temperature can go up by at most 10 °C and is never set to 0 (in Orca, 0 means the filament does not support that plate); flow ratio stays between 0.8 and 1.2; max volumetric speed can go up by at most 10%; speeds, accelerations and jerk stay within the printer's machine limits.

No software check replaces your own judgement: look at what a proposal changes before you apply it.

These rules are covered by tests in `tests/`, which run without OrcaSlicer: `python3 -m unittest discover tests`.

## Skills

The AI works from troubleshooting guides in `skills/` (defects, materials, calibration, printers, goals). They are written from public documentation; each file lists its sources.

The guides are embedded in `print_doctor.py`. After editing a file in `skills/`, run:

```
python3 incorpora_skill.py
```

You can also drop your own `.md` skills in the plugin's `skills` folder (its path is shown in the settings); a skill with the same name replaces the embedded one.

## Problems, questions, ideas

- **Something does not work?** Press **Report a problem** at the bottom of the panel. Your browser opens a GitHub issue with the version, OrcaSlicer version and system already filled in, and the folder with `print_doctor_report.txt` opens next to it: drag that file into the issue. The file holds the plugin log with keys, tokens, email addresses and your user folder removed. Read it before you attach it if you like.
- **Questions and help:** [Discussions](https://github.com/MarcoPiazza83/Print-Doctor/discussions).
- **Ideas:** press **Suggest an idea** at the bottom of the panel, or [open a feature request](https://github.com/MarcoPiazza83/Print-Doctor/issues/new?template=feature.yml).
- **No GitHub account?** After either button, the chat shows **Write an email**: it opens your mail app with a message to info@meshdab.com already filled in. For a problem, attach the same file.
- **Security problems:** see [SECURITY.md](SECURITY.md), do not open a public issue.

English or Italian, both are fine.

## Support the project

Print Doctor is free. If it helps you, you can [buy me a coffee](https://buymeacoffee.com/Marco.Piazza).

## License

GNU Affero General Public License v3.0, see [LICENSE](LICENSE).

Print Doctor is an independent project. It is not affiliated with or endorsed by OrcaSlicer, OpenAI, Anthropic, Google, OpenRouter, Bambu Lab or Prusa Research.
