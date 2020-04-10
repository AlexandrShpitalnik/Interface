from GUI import GUI
from pharmacy import Env
from pharmacy import Randomizer


if __name__ == '__main__':
    drugs_file = 'drugs_big.txt'
    orders_file = 'reccuring.txt'

    gui = GUI('GUI', 'org.beeware.gui')
    randomizer = Randomizer
    env = Env(GUI=gui, randomizer_cls=randomizer, drugs_file=drugs_file, orders_file=orders_file)
    gui.init_env(env)
    gui.main_loop()
