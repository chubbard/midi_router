import mido
import cmd2
from cmd2 import CompletionItem
import readline
import sys

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
    def __init__(self, inputName:str):
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
        if len(routes) < 1:
            print("No routes defined")

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
        print(f"Removing route {route}")
        route = self.routes[index]
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
    routes = [
#        MidiRoute("HYDRASYNTH EXPLORER 3").addRoute("KOBOL EXPANDER 6", "MODEL D 5")
    ]
    router = MidiRouterConsole()
    try:
        router.cmdloop()
    finally:        
        router.close()
        print("Goodbye.")
    sys.exit(0)

