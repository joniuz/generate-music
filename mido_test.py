import mido
import time

try:
    outport = mido.open_output()
    drum = [36,38,43,50,42,46,39,75,67,49]
    while 1:
        for note in drum:
            midi_message = mido.Message('note_on', channel=0, note=note, velocity=64)
            print(midi_message)
            outport.send(midi_message)
            time.sleep(0.25)
            midi_message = mido.Message('note_off', channel=0, note=note, velocity=64)
            print(midi_message)
            outport.send(midi_message)
            time.sleep(0.25)
    
except Exception as e:
    print(f"Error opening or sending to port: {e}")
