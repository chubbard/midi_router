# midi_router

## Why

MIDI Router is a simple portable router for MIDI messages that makes hooking
hardware USB devices simple.  There is no need for a DAW to route MIDI messages.
Windows 11 particularly lacks a MIDI routing solution out of the box.

## Install

You'll need Python 3.12.  Newer versions of Python will not work on Windows 
platform at this time.  Copy the midi_router files to a directory then use 
the navigate a terminal to that directory and execute:

```
python -m pip install -r requirements.txt
```

## Establishing A Route

To run midi_router all you need to do is execute the python scripts.

```
python midi_router.py
```

To establish the first route use the `route` command:

```
midi > route "MIDI IN Device 1" "MIDI OUT Device 2" "MIDI OUT Device 3"
```

## View The State

To display the active routes use the `routes` command:

```
midi > routes
```

To see all MIDI devices registered with the system use the `list` command:

```
midi > list
```

## Edit Routes

To delete a route use the `delete` command and the route number:

```
midi > delete 1
```

## Monitor

To monitor a MIDI port for MIDI messages use the `monitor` command:

```
midi > monitor "MIDI IN Device 1"
```

Hit `ENTER` to stop monitoring the port.
