import random
import math
import datetime
import time

# Based off of https://hackernoon.com/genetic-algorithms-explained-a-python-implementation-sd4w374i

from simulation_evaluation.microgrid_simulator import ControllEnvironment


class MicrogridGA:

    def __init__(self, generations, size, day_nr=18, precision=1, battery_power=21.1, battery_max_discharge=40.0,
                 pv_scale=1.0, priorities=[1, 2, 3, 4, 5, 6, 7],
                 step_type="percentage", mutate_chance=0.2,
                 elit_perc=0.05, cross_perc=0.25, mutate_perc=0.25, corrs_mut_perc=0.25):

        self.battery_power = battery_power
        self.battery_max_discharge = battery_max_discharge
        self.pv_scale = pv_scale
        self.priorities = priorities
        self.precision = precision
        self.test_env = ControllEnvironment(day_nr=day_nr, battery_power=battery_power,
                                            battery_max_discharge=battery_max_discharge, pv_scale=pv_scale,
                                            priorities=priorities)
        self.generations = generations
        self.size = size
        self.mutate_chance = mutate_chance
        self.step_type = step_type
        self.best = None
        self.best_score = None
        self.elit_perc = elit_perc
        self.cross_perc = cross_perc
        self.mutate_perc = mutate_perc
        self.corrs_mut_perc = corrs_mut_perc
        self.history = {}
        self.population = None
        self.best_score = -99999999.999
        self.best = None

    def save_best(self):
        applied = self.test_env.step_24h(self.best, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        self.test_env.save_result(applied)

    def get_history(self):
        return self.history

    def get_deployed_best(self):
        applied = self.test_env.step_24h(self.best, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        return applied

    def get_original(self):
        return self.test_env.input_df.reset_index(drop=True)

    def generate_population(self, size_pop):
        population = []
        for i in range(size_pop):
            individual = {"Nursery1_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery1_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery2_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Nursery2_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Playground_Lights_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Playground_Sockets_Quota": [round(random.random(), self.precision) for x in range(0, 24)],
                          "Streetlights_Quota": [round(random.random(), self.precision) for x in range(0, 24)]
                          }
            population.append(individual)
        return population

    def evaluate_individual(self, individual):
        return sum(individual['Battery_SoC']) / 100.0 / 24.0

    def apply_function(self, individual):
        applied = self.test_env.step_24h(individual, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        return self.evaluate_individual(applied)

    def get_deployed(self, individual):
        applied = self.test_env.step_24h(individual, battery_power=self.battery_power, pv_scale=self.pv_scale,
                                         step_type=self.step_type)
        return applied

    def evaluate_population(self, population):
        ret = {}
        for pop in population:
            ret[self.apply_function(pop)] = pop
        return ret

    def choice_by_roulette(self, sorted_population, fitness_sum):
        offset = 0
        normalized_fitness_sum = fitness_sum

        lowest_fitness = min(sorted_population)
        if lowest_fitness < 0:
            offset = -lowest_fitness
            normalized_fitness_sum += offset * len(sorted_population)

        draw = random.uniform(0, 1)

        accumulated = 0
        for fitness_orig in sorted(sorted_population, reverse=True):
            fitness = offset + fitness_orig
            probability = fitness / normalized_fitness_sum
            accumulated += probability

            if draw <= accumulated:
                return sorted_population[fitness_orig]

    def random_select(self, evaluated_pop):
        key = random.choice(list(evaluated_pop.keys()))
        return evaluated_pop[key]

    def crossover_archive(self, individual_a, individual_b):
        new_individual = {}
        if random.random > 0.5:
            for dev in individual_a:
                new_individual[dev] = []
                for i, _ in enumerate(individual_a[dev]):
                    # Mean
                    new_individual[dev].append(
                        round((individual_a[dev][i] + individual_b[dev][i]) / 2.0, self.precision))
        else:
            for dev in individual_a:
                new_individual[dev] = []
                for i, _ in enumerate(individual_a[dev]):
                    # Select
                    new_individual[dev].append(random.choice([individual_a[dev][i], individual_b[dev][i]]))
        return new_individual

    def crossover(self, individual_a, individual_b):
        new_individual = {}
        for dev in individual_a:
            new_individual[dev] = []
            for i, _ in enumerate(individual_a[dev]):
                # Mean
                new_individual[dev].append(round((individual_a[dev][i] + individual_b[dev][i]) / 2.0, self.precision))
        return new_individual

    def mutate_archive(self, individual):
        if random.random > 0.5:
            # New Value Randoms
            for dev in individual:
                for i, _ in enumerate(individual[dev]):
                    # Random Full Mutation of value
                    if random.random() > self.mutate_chance:
                        individual[dev][i] = round(random.random(), self.precision)
        else:
            # Modify Mutate
            for dev in individual:
                for i, _ in enumerate(individual[dev]):
                    if random.random() > self.mutate_chance:
                        if random.random() > 0.5:
                            new_val = round(individual[dev][i] + individual[dev][i] / 2, self.precision)
                        else:
                            new_val = round(individual[dev][i] - individual[dev][i] / 2, self.precision)
                        if new_val > 1.0:
                            new_val = 1.0
                        if new_val <= 0.0:
                            new_val = 0.0
                        individual[dev][i] = new_val
        return individual

    def mutate(self, individual):
        for dev in individual:
            for i, _ in enumerate(individual[dev]):
                # Random Full Mutation of value
                if random.random() > self.mutate_chance:
                    individual[dev][i] = round(random.random(), self.precision)
        return individual

    def make_next_generation(self, evaluated_population):
        next_generation = []
        population_size = self.size
        fitness_sum = sum(evaluated_population.keys())

        # Sizes
        elit_size = int(population_size * self.elit_perc)
        cross_size = int(population_size * self.cross_perc)
        mutation_size = int(population_size * self.mutate_perc)
        corss_mut_size = int(population_size * self.corrs_mut_perc)
        random_size = population_size - elit_size - cross_size - mutation_size - corss_mut_size
        print("Sizes - Original:", len(evaluated_population), " Elit:", elit_size, " Cross:", cross_size, " Mut:",
              mutation_size,
              " CrossMut:", corss_mut_size, " Random:", random_size)
        i = 0
        for score in sorted(evaluated_population, reverse=True):
            next_generation.append(evaluated_population[score])
            i += 1
            if i >= elit_size:
                break
        #Only use top half of population
        evaluated_population = {k: evaluated_population[k] for k in sorted(list(evaluated_population),reverse=True)[:len(evaluated_population)//2]}

        # Crossover
        for i in range(cross_size):
            first_choice = None
            second_choice = None

            # Safe Wheel
            while first_choice is None:
                first_choice = self.random_select(evaluated_population)
                # first_choice = self.choice_by_roulette(evaluated_population, fitness_sum)
            while second_choice is None:
                second_choice = self.random_select(evaluated_population)
                # second_choice = self.choice_by_roulette(evaluated_population, fitness_sum)
            individual = self.crossover(first_choice, second_choice)
            next_generation.append(individual)

        # Mutate
        for i in range(mutation_size):
            first_choice = None

            # Safe Wheel
            while first_choice is None:
                first_choice = self.random_select(evaluated_population)
                # first_choice = self.choice_by_roulette(evaluated_population, fitness_sum)
            individual = self.mutate(first_choice)
            next_generation.append(individual)

        # Cross Mutate
        for i in range(corss_mut_size):
            first_choice = None
            second_choice = None

            # Safe Wheel
            while first_choice is None:
                first_choice = self.random_select(evaluated_population)
                # first_choice = self.choice_by_roulette(evaluated_population, fitness_sum)
            while second_choice is None:
                second_choice = self.random_select(evaluated_population)
                # second_choice = self.choice_by_roulette(evaluated_population, fitness_sum)

            individual = self.crossover(first_choice, second_choice)
            individual = self.mutate(individual)

            next_generation.append(individual)

        # Random
        for individual in self.generate_population(random_size):
            next_generation.append(individual)

        return next_generation

    def do_step(self, step):
        evaluated_population = self.evaluate_population(self.population)
        if max(evaluated_population) > self.best_score:
            self.best = evaluated_population[max(evaluated_population)]
            self.best_score = max(evaluated_population)
        self.history[step] = [self.best_score, self.best, time.time() - self.start]
        # print("New pop utils:",sorted(list(evaluated_population.keys()),reverse=True))
        self.population = self.make_next_generation(evaluated_population)

    def run(self):
        self.start = time.time()
        self.population = self.generate_population(self.size)
        i = 0
        while True:
            print(f"🧬 GENERATION {i}")
            print("Started: ", datetime.datetime.now())
            self.do_step(i)
            print("Best Individual: ", self.best)
            print("Best Score: ", self.best_score)
            print("Elapsed Time:", time.time() - self.start)
            i += 1
            if i == self.generations:
                break

        print("\n🔬 FINAL RESULT")
        print("Best Individual: ", self.best)
        print("Best Score: ", self.best_score)
        print("Elapsed Time:", time.time() - self.start)
        # self.save_best()
        # print("Best Individual saved to output_data.csv")
        print("History: ", [self.history[x][0] for x in self.history])
#
# day_nr=18
# precision=1
# battery_power=4.1
# battery_max_discharge = 40.0
# pv_scale=0.4
# priorities=[1, 2, 3, 4, 5, 6, 7]
# gens = 2
# size = 25
#
# my_ga2 = MicrogridGA(gens, size,day_nr=day_nr, precision=precision, battery_power=battery_power,
#                                                battery_max_discharge = battery_max_discharge, pv_scale=pv_scale,
#                     priorities=priorities,step_type="percentage", mutate_chance=0.4, elit_perc=0.05
#                     ,cross_perc=0.15,mutate_perc=0.15,corrs_mut_perc=0.10)
# #Redefine to new function
# my_ga2.run()
