import click
from datetime import datetime
from typing import List, Dict
from midiutil import MIDIFile
#from pyo import *
import random
import mido
import time
import os

from algorithms.genetic import generate_genome, Genome, selection_pair, single_point_crossover, mutation

BITS_PER_NOTE = 4
KEYS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]

NAME_TO_SEMITONE = {
    "C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"Fb":4,"E#":5,"F":5,"F#":6,"Gb":6,
    "G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11,"Cb":11,"B#":0
}

def midi_number(note_name: str, octave: int) -> int:
    # MIDI: C4=60; C-1=0
    return 12 * (octave + 1) + NAME_TO_SEMITONE[note_name]

SCALE_PATTERNS = {
    "major":              [2,2,1,2,2,2,1],  # Major
    "minorN":             [2,1,2,2,1,2,2],  # Natural minor
    "minorH":             [2,1,2,2,1,3,1],  # Harmonic minor
    "minorM":             [2,1,2,2,2,2,1],  # Melodic minor asc
    "pentamajor":         [2,2,3,2,3],      # Pentatonic major
    "pentaminor":         [3,2,2,3,2],      # Pentatonic minor
    "bluesminor":         [3,2,1,1,3,2],    # Blues minor
    "ionian":             [2,2,1,2,2,2,1],  # Ionian
    "dorian":             [2,1,2,2,2,1,2],  # Dorian
    "phrygian":           [1,2,2,2,1,2,2],  # Phrygian
    "lydian":             [2,2,2,1,2,2,1],  # Lydian
    "mixolydian":         [2,2,1,2,2,1,2],  # Mixolydean
    "aeolian":            [2,1,2,2,1,2,2],  # Aeolidian
    "locrian":            [1,2,2,1,2,2,2],  # Locrian
}

def build_scale(root: str, octave: int, scale: str, degrees: int = 8, prefer_sharps=True):
    if scale not in SCALE_PATTERNS:
        raise ValueError(f"Unknown scale '{scale}'. Available: {list(SCALE_PATTERNS.keys())}")
    current = midi_number(root, octave)
    pattern = SCALE_PATTERNS[scale]
    result = [current]
    step_idx = 0
    for deg in range(2, degrees + 1):
        current += pattern[step_idx % len(pattern)]
        result.append(current)
        step_idx += 1
    return result

def int_from_bits(bits: List[int]) -> int:
    return int(sum([bit*pow(2, index) for index, bit in enumerate(bits)]))


def genome_to_melody(genome: Genome, num_bars: int, num_notes: int, num_steps: int,
                     pauses: int, key: str, scale: str, root: int) -> Dict[str, list]:
    notes = [genome[i * BITS_PER_NOTE:i * BITS_PER_NOTE + BITS_PER_NOTE] for i in range(num_bars * num_notes)]

    note_length = 4 / float(num_notes)

    #print("Scale generation:")
    #print("root : " + str(key))
    #print("Scale: " + str(scale))
    #print("First: " + str(key) + str(root))

    scl = build_scale(root=key, octave=root, scale=scale, degrees=15, prefer_sharps=True)
    # Print the scale for debug purpose
    #print(scl)

    melody = {
        "notes": [],
        "velocity": [],
        "beat": []
    }

    for note in notes:
        integer = int_from_bits(note)

        if not pauses:
            integer = int(integer % pow(2, BITS_PER_NOTE - 1))

        if integer >= pow(2, BITS_PER_NOTE - 1):
            melody["notes"] += [0]
            melody["velocity"] += [0]
            melody["beat"] += [note_length]
        else:
            if len(melody["notes"]) > 0 and melody["notes"][-1] == integer:
                melody["beat"][-1] += note_length
            else:
                melody["notes"] += [integer]
                melody["velocity"] += [127]
                melody["beat"] += [note_length]

    steps = []
    for step in range(num_steps):
        steps.append([scl[(note+step*2) % len(scl)] for note in melody["notes"]])

    melody["notes"] = steps
    return melody


def genome_to_events(genome: Genome, num_bars: int, num_notes: int, num_steps: int,
                     pauses: bool, key: str, scale: str, root: int, bpm: int):
    melody = genome_to_melody(genome, num_bars, num_notes, num_steps, pauses, key, scale, root)

    # This function was intended to use the python library pyo and its Events structure, now is not used
    return melody

def play_midi_events(midi_out, events):
    # Function to play the Events structure
    for midi_event in range(len(events["velocity"])):
        midi_message = mido.Message('note_on', channel=0, note=events["notes"][0][midi_event], velocity=events["velocity"][midi_event])
        #print(midi_message)
        midi_out.send(midi_message)
        time.sleep(int(events["beat"][midi_event])/6) # This division by 6 define the BPM, ideally it must be a parameter
        midi_message = mido.Message('note_off', channel=0, note=events["notes"][0][midi_event], velocity=events["velocity"][midi_event])
        #print(midi_message)
        midi_out.send(midi_message)

def fitness(genome: Genome, midi_out, num_bars: int, num_notes: int, num_steps: int,
            pauses: bool, key: str, scale: str, root: int, bpm: int) -> int:
    
    # BPM is not used 
    #m = metronome(bpm)

    events = genome_to_events(genome, num_bars, num_notes, num_steps, pauses, key, scale, root, bpm)

    print("Playing song ...")
    play_midi_events(midi_out, events)
    rating = input("Rating (0-5): ")
    time.sleep(1)

    try:
        rating = int(rating)
    except ValueError:
        rating = 0

    return rating

# This function is not used

#def metronome(bpm: int):
#    met = Metro(time=1 / (bpm / 60.0)).play()
#    t = CosTable([(0, 0), (50, 1), (200, .3), (500, 0)])
#    amp = TrigEnv(met, table=t, dur=.25, mul=1)
#    freq = Iter(met, choice=[660, 440, 440, 440])
#    return Sine(freq=freq, mul=amp).mix(2).out()


def save_genome_to_midi(filename: str, genome: Genome, num_bars: int, num_notes: int, num_steps: int,
                        pauses: bool, key: str, scale: str, root: int, bpm: int):
    melody = genome_to_melody(genome, num_bars, num_notes, num_steps, pauses, key, scale, root)

    if len(melody["notes"][0]) != len(melody["beat"]) or len(melody["notes"][0]) != len(melody["velocity"]):
        raise ValueError

    mf = MIDIFile(1)

    track = 0
    channel = 0

    time = 0.0
    mf.addTrackName(track, time, "Sample Track")
    mf.addTempo(track, time, bpm)

    for i, vel in enumerate(melody["velocity"]):
        if vel > 0:
            for step in melody["notes"]:
                mf.addNote(track, channel, step[i], time, melody["beat"][i], vel)

        time += melody["beat"][i]

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        mf.writeFile(f)

@click.command()
@click.option("--num-bars", default=8, prompt='Number of bars', type=int)
@click.option("--num-notes", default=4, prompt='Notes per bar', type=int)
@click.option("--num-steps", default=1, prompt='Number of steps', type=int)
@click.option("--pauses", default=True, prompt='Introduce Pauses?', type=bool)
@click.option("--key", default="C", prompt='Key', type=click.Choice(KEYS, case_sensitive=False))
@click.option("--scale", default="major", prompt='Scale', type=click.Choice(SCALE_PATTERNS, case_sensitive=False))
@click.option("--root", default=4, prompt='Scale Root', type=int)
@click.option("--population-size", default=10, prompt='Population size', type=int)
@click.option("--num-mutations", default=2, prompt='Number of mutations', type=int)
@click.option("--mutation-probability", default=0.5, prompt='Mutations probability', type=float)
@click.option("--bpm", default=128, type=int)
def main(num_bars: int, num_notes: int, num_steps: int, pauses: bool, key: str, scale: str, root: int,
         population_size: int, num_mutations: int, mutation_probability: float, bpm: int):

    
    folder = str(int(datetime.now().timestamp()))

    population = [generate_genome(num_bars * num_notes * BITS_PER_NOTE) for _ in range(population_size)]

    midi_out = mido.open_output()

    population_id = 0

    running = True
    while running:
        random.shuffle(population)

        population_fitness = [(genome, fitness(genome, midi_out, num_bars, num_notes, num_steps, pauses, key, scale, root, bpm)) for genome in population]

        sorted_population_fitness = sorted(population_fitness, key=lambda e: e[1], reverse=True)

        population = [e[0] for e in sorted_population_fitness]

        next_generation = population[0:2]

        for j in range(int(len(population) / 2) - 1):

            def fitness_lookup(genome):
                for e in population_fitness:
                    if e[0] == genome:
                        return e[1]
                return 0

            parents = selection_pair(population, fitness_lookup)
            offspring_a, offspring_b = single_point_crossover(parents[0], parents[1])
            offspring_a = mutation(offspring_a, num=num_mutations, probability=mutation_probability)
            offspring_b = mutation(offspring_b, num=num_mutations, probability=mutation_probability)
            next_generation += [offspring_a, offspring_b]

        print(f"Population {population_id} done")

        events = genome_to_events(population[0], num_bars, num_notes, num_steps, pauses, key, scale, root, bpm)
        input("==> Here is the no1 hit ...     [Press Enter]")
        play_midi_events(midi_out, events)
        time.sleep(1)

        events = genome_to_events(population[1], num_bars, num_notes, num_steps, pauses, key, scale, root, bpm)
        input("==> Here is the second best ... [Press Enter]")
        play_midi_events(midi_out, events)
        time.sleep(1)

        print("Saving population midi ...")
        for i, genome in enumerate(population):
            save_genome_to_midi(f"{folder}/{population_id}/{scale}-{key}-{i}.mid", genome, num_bars, num_notes, num_steps, pauses, key, scale, root, bpm)
        print("Done")

        running = input("Continue? [Y/n]") != "n"
        population = next_generation
        population_id += 1


if __name__ == '__main__':
    print("=== Genetic Algorithm Music ===")
    main()
