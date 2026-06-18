import mido
import cmd2
from cmd2 import CompletionItem
import readline
import sys
import json
import re
from pathlib import Path

class MidiPort:
    def __init__(self, midi_port):
        self.port = midi_port
        self.callbacks = []
        self.attach()
        
    @property
    def name(self):
        return self.port.name
        
    def listen(self,callback):
        self.callbacks.append(callback)
    
    def unlisten(self,callback):
        self.callbacks.remove(callback)
        
    def attach(self):
        self.port.callback = self.receive
        
    def receive(self, msg):
        for callback in self.callbacks:
            callback(msg)

class MidiInPort(MidiPort):
    def __init__(self, name):
        super().__init__(mido.open_input(name) )

class MidiOutPort(MidiPort):
    def __init__(self, name):
        super().__init__(mido.open_output(name) )

    def send(self, msg):
        self.port.send(msg)

class Midi:
    midi_in = {}
    midi_out = {}
    
    def open_input(name:str) -> MidiInPort:
        if name not in Midi.midi_in:
            Midi.midi_in[name] = MidiInPort(name)
        return Midi.midi_in[name]
        
    def open_output(name:str) -> MidiOutPort:
        if name not in Midi.midi_out:
            Midi.midi_out[name] = MidiOutPort(name)
        return Midi.midi_out[name]
        
    def find_in_port(port_name:str) -> MidiPort:
        """Find an in port by partial name"""
        for name in mido.get_input_names():
            if port_name in name:
                return Midi.open_input(name)
        
    def find_out_port(port_name:str) -> MidiPort:
        """Find an out port by partial name"""
        for name in mido.get_output_names():
            if port_name in name:
                return Midi.open_output(name)

    def find_port(portName:str) -> MidiPort:
        for name in mido.get_input_names():
            if portName == name:
                return Midi.open_input(name)
                
        for name in mido.get_output_names():
            if portName == name:
                return Midi.open_output(name)
                    
    def find_all(prefix:str = '') -> dict:
        hits = {
            "input": [],
            "output": []
        }
        for name in mido.get_input_names():
            if name.startswith(prefix):
                hits["input"].append(name)
                
        for name in mido.get_output_names():
            if name.startswith(prefix):
                hits["output"].append(name)
                
        return hits

class MidiRoute:
    def __init__(self, inputName:str = None):
        if inputName:
            self.inport = Midi.open_input(inputName)
            self.outports = []
        
    def add_route(self, *args):
        for p in args:
            self.outports.append( Midi.open_output(p) )
        return self
        
    def listen(self):
        self.inport.listen( self.receive )
        return self
        
    def receive(self,msg):
        for p in self.outports:
            p.send( msg )
        
    def close(self):
        self.inport.unlisten(self.receive)
        for p in self.outports:
            p.port.panic()
            
    def to_save(self):
        """Map this route to a saved object format"""
        return { 
            "inport": clean_port_name( self.inport.name ),
            "outports": [ clean_port_name( op.name ) for op in self.outports ] 
        }
        
    def from_restore(self, json):
        """Given a saved object restore this route"""
        self.inport = Midi.find_in_port(json['inport'])
        self.outports = [ Midi.find_out_port( op ) for op in json['outports'] ]
        return self
        

def clean_port_name(port_name):
    
    # 1. Strip Linux ALSA address patterns like " 128:0" or ":0" at the end
    cleaned = re.sub(re.compile(r'\s*\d+:\d+$'), '', port_name)
    cleaned = re.sub(re.compile(r':\d+$'), '', cleaned)
    
    # 2. Strip common Windows instance suffixes like " 1", " 2", etc. at the end
    cleaned = re.sub(re.compile(r'\s+\d+$'), '', cleaned)
    
    # 3. Strip Windows instance prefixes like "1- ", "2- " at the start
    cleaned = re.sub(re.compile(r'^\d+-\s*'), '', cleaned)
    
    # 4. Strip extra brackets or standalone numbers often added by RtMidi
    cleaned = re.sub(re.compile(r'\s*\(\d+\)$'), '', cleaned)

    return cleaned.strip()

class MidiRouterConsole(cmd2.Cmd):
    
    def __init__(self):
        super().__init__()
        self.intro = "Welcome to MIDI router.  If you need help type 'help' or '?'  Let's get to routing some MIDI..."
        self.prompt = "midi > "
        self.default_category = "MIDI Router Commands"
        self.routes = []
    
    def do_list(self, arg):
        """List the USB ports that are available"""
        print("--- INPUT DEVICES ---")
        for name in mido.get_input_names():
            print(f"  '{name}'")

        print("\n--- OUTPUT DEVICES ---")
        for name in mido.get_output_names():
            print(f"  '{name}'")
            
    def do_routes(self, arg):
        """List the routes defined."""
        for index,route in enumerate(self.routes):
            print(f"{index+1}\t{route.inport.name} >>")
            for port in route.outports:
                print(f"\t\t-> {port.name}")
        if len(self.routes) < 1:
            print("No routes defined")
            
    def do_save(self,args):
        """Save routes"""
        midi_router_dir = Path.home() / '.midi_router/'
        midi_router_dir.mkdir(parents=True,exist_ok=True)
        with open(midi_router_dir / 'routes.json', 'w') as f:
            json.dump([route.to_save() for route in self.routes], f)
        print(f"Saved {len(self.routes)} routes")
            
    def do_restore(self,args):
        """Load all previously saved routes.  This preserves any existing routes."""
        prior_routes = len(self.routes)
        midi_router_dir = Path.home() / '.midi_router/'
        midi_router_dir.mkdir(parents=True,exist_ok=True)
        with open(midi_router_dir / 'routes.json', 'r') as f:
            saved_routes = json.load( f )
            self.routes = self.routes + [ MidiRoute().from_restore( json ) for json in saved_routes ]
        print(f"Restored {len(self.routes)-prior_routes} routes")

    def midi_in_provider(self) -> list:
        results = Midi.find_all()
        return [CompletionItem(display_meta="In", value=r) for r in results["input"]]

    def midi_out_provider(self) -> list:
        results = Midi.find_all()
        return [CompletionItem(display_meta="Out", value=r) for r in results["output"]]

    def midi_port_provider(self) -> list:
        results = Midi.find_all()
        return [CompletionItem(display_meta="In", value=r) for r in results["input"]] + [CompletionItem(display_meta="Out", value=r) for r in results["output"]]

    def route_remove_provider(self) -> list:
        return [i for i in range(1,len(self.routes))]

    routeParser = cmd2.Cmd2ArgumentParser()
    routeParser.add_argument("input", help="MIDI In Port", choices_provider=midi_in_provider)
    routeParser.add_argument("outputs", help="MIDI Out Ports to route from the in into the out.", nargs="+", choices_provider=midi_out_provider)
    @cmd2.with_argparser(routeParser)
    def do_route(self,args):
        route = MidiRoute(args.input)
        for out in args.outputs:
            route.add_route(out)
        self.routes.append( route )
        route.listen()

    removeRouteParser = cmd2.Cmd2ArgumentParser()
    removeRouteParser.add_argument("route", help="Route number to remove", type=int, choices_provider=route_remove_provider)
    @cmd2.with_argparser(removeRouteParser)
    def do_delete(self,args):
        index = args.route
        route = self.routes[index-1]
        if route:
            self.routes.remove( route )
        print(f"Removed route {index}")

    portParser = cmd2.Cmd2ArgumentParser()
    portParser.add_argument("port", help="MIDI port to monitor", choices_provider=midi_port_provider)
    @cmd2.with_argparser(portParser)
    def do_monitor(self, args):
        """Monitor a MIDI port"""
        monitored_port = Midi.find_port(args.port)
        if monitored_port:
            print("Press Enter to stop monitoring")
            monitored_port.listen(self.monitor_port)
            input()
            monitored_port.unlisten(self.monitor_port)
            print("Done.")
        else:
            print(f"Could not find {args.port}")
    
    def monitor_port(self,msg):
        print(msg)
    
    def close(self):
        for route in self.routes:
            route.close()
            
 
if __name__ == '__main__':
    router = MidiRouterConsole()
    try:
        router.cmdloop()
    finally:        
        router.close()
        print("Goodbye.")
    sys.exit(0)

