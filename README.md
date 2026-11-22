# Print Doctor

AI print troubleshooting for OrcaSlicer.

Print Doctor is a plugin for OrcaSlicer 2.5.1 or newer. It adds a chat panel: you describe a print problem (stringing, warping, supports that will not come off, a rough top surface...) or attach a photo, the AI reads your current Orca settings and proposes changes to the process and filament presets. Nothing changes until you press Apply, and every applied change can be undone.

> **Status: beta.** The code is covered by automated tests that run outside OrcaSlicer. Testing inside OrcaSlicer is still in progress, so expect rough edges.

*In italiano: Print Doctor è un plugin per OrcaSlicer con una chat. Descrivi il difetto di stampa, l'IA legge i parametri di Orca e propone le modifiche, che applichi con un clic e puoi annullare. L'interfaccia è in italiano e in inglese.*

## Install

1. Download `print_doctor.py`.
2. In OrcaSlicer: **File → Plugins → Install local plugin**, pick the file, activate it and accept the permissions (network and threads).
3. Select **Print Doctor** in the Plugins window and press **Run**: the panel opens on the right.
4. Open the settings (gear icon) and connect an AI service.

## AI services

| Service | How you connect |
|---|---|
| ChatGPT | "Continue with ChatGPT": uses your own ChatGPT plan through OpenAI's official sign-in for open-source apps (preview) |
| OpenRouter | Browser sign-in, or an API key |
| Anthropic, OpenAI, Google Gemini | Your own API key |
| Ollama, LM Studio | Local models, no key |
| Any OpenAI-compatible server | Base URL and key |

Requests go straight from your computer to the service you choose. Keys and tokens are stored only on your computer, in the plugin's settings file.

## Safety rules

The plugin enforces these in code, twice: when the AI proposes a change and again before it is applied.

- Printer settings are never changed.
- Custom G-code, post-processing scripts, material data, temperature ranges and chamber heating are never changed.
- Only settings on an explicit allow-list can be changed, each with a type and a range. Anything else is explained to you as a manual step.
- Nozzle temperature stays inside the filament's own range; plate temperature can go up by at most 10 °C; flow ratio stays between 0.8 and 1.2; max volumetric speed can go up by at most 10%; speeds, accelerations and jerk stay within the printer's machine limits.

No software check replaces your own judgement: look at what a proposal changes before you apply it.

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
