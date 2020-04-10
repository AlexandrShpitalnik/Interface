import numpy as np
import copy
import csv

from GUI import GUI


class ClientOrder:
    def __init__(self, meta, card_id, drugs, loyal_client=False):
        self.client_name = meta[0]
        self.phone_number = meta[2]
        self.address = meta[1]
        self.drugs = drugs
        self.loyal_client = loyal_client
        self.card_id = card_id
        self.ready_drugs = {}
        self.total_profit = 0


class RecurringOrder:
    def __init__(self, meta, card_id, drugs, period):
        self.__client_order = ClientOrder(meta, card_id, drugs, True)
        self.period = period
        self.last_order = None

    def get_client_order(self):
        return copy.deepcopy(self.__client_order)


class DrugInfo:
    def __init__(self, params):
        self.name = params[0]
        self.group = ""
        self.form = ""
        self.dose = None
        self.standard_quantity = params[3]
        self.base_price = params[1]
        self.cur_price = params[1] * params[2]
        self.base_profit = params[2]
        self.cur_profit = params[2]
        self.shelf_life = params[4]


class DrugBatch:
    def __init__(self, drug_name, quantity, valid_to):
        self.drug_name = drug_name
        self.valid_to = valid_to
        self.quantity = quantity


class Randomizer:
    def __init__(self):
        self.__base_prices = []
        self.__profits = []
        self.__average_drugs_in_order = 3
        self.__order_var = 1
        self.__card_proba = None
        self.__max_card_id = 10000
        self.__min_wainting_time = 1
        self.__max_waiting_time = 3
        self.__order_scale = None

    def init_user_params(self, card_proba, order_scale):
        self.__card_proba = card_proba
        self.__order_scale = order_scale

    def init_params(self, prices, profits):
        self.__profits = profits
        self.__base_prices = prices

    def update_profits(self, new_profits):
        self.__profits = new_profits

    def __price_to_clients(self, x):
        price = x[0]
        profit = x[1]
        arg = price * (profit ** 2)
        arg = -np.log(arg) * 2 + 12
        res = self.__order_scale * (np.exp(arg) / (1 + np.exp(arg)))
        return res

    def start_new_day(self):
        average_boughts = np.apply_along_axis(self.__price_to_clients, axis=0, arr=[self.__base_prices, self.__profits])
        bought_drugs = np.random.poisson(average_boughts)
        generated_orders_info = []
        while True:
            meta, card_id, ordered_drugs_ids = self.__generate_order_info(bought_drugs)
            if ordered_drugs_ids:
                generated_orders_info.append((meta, card_id, ordered_drugs_ids))
            else:
                break
        return generated_orders_info

    def __generate_order_info(self, bought_drugs):
        meta = self.__generate_meta()
        card_id = self.__generate_card_id()
        ordered_drugs_ids = {}
        n_drugs_in_order = round(np.random.normal(self.__average_drugs_in_order, self.__order_var))
        i = 0
        while np.sum(bought_drugs) != 0 and i < n_drugs_in_order:
            i += 1
            drugs_proba = bought_drugs / np.sum(bought_drugs)
            drug_id = np.random.choice(len(self.__base_prices), p=drugs_proba)
            if drug_id in ordered_drugs_ids:
                ordered_drugs_ids[drug_id] += 1
            else:
                ordered_drugs_ids[drug_id] = 1
            bought_drugs[drug_id] -= 1

        return meta, card_id, ordered_drugs_ids

    def __generate_card_id(self):
        if np.random.binomial(1, self.__card_proba):
            return np.random.randint(1, self.__max_card_id)
        return None

    def __generate_meta(self):
        # todo add true generation
        # (name, address, phone_number)
        return 'A', 'B', 'C'

    def generate_waiting_time(self):
        return round(np.random.uniform(self.__min_wainting_time, self.__max_waiting_time))


class Env:
    def __init__(self, GUI, randomizer_cls, drugs_file, orders_file):
        self.GUI = GUI
        self.__drugs_names = []
        names, prices, profits, quants, life = self.__load_drugs_info(drugs_file)
        recurring_orders = self.__load_orders_info(orders_file)
        self.randomizer = randomizer_cls()# todo - init
        self.randomizer.init_params(prices, profits)
        self.pharmacy = Pharmacy(names, prices, profits, quants, life, recurring_orders)

        self.cur_day = 0
        self.n_days = None
        self.order_history = []
        self.pharmacy_orders_queue = []

    def init_user_parameters(self, params):
        card_proba = params.card_proba
        orders_scale = params.orders_scale
        couriers = params.couriers
        card_sale = params.card_sale
        quant_to_reorder = params.quant_to_reorder
        self.n_days = params.n_days
        self.randomizer.init_user_params(card_proba, orders_scale)
        self.pharmacy.init_user_params(couriers, card_sale, quant_to_reorder)

    def __load_drugs_info(self, filename):
        names = []
        prices = []
        profits = []
        quants = []
        life = []
        with open(filename) as file:
            reader = csv.reader(file, delimiter=';')
            reader.__next__()
            for line in reader:
                name = line[0]
                names.append(name)
                prices.append(int(line[1]))
                profits.append(float(line[2]))
                quants.append(int(line[3]))
                life.append(int(line[4]))

                self.__drugs_names.append(name)
        return names, prices, profits, quants, life

    def __load_orders_info(self, filename):
        orders = []
        with open(filename) as file:
            reader = csv.reader(file, delimiter=';')
            reader.__next__()
            for line in reader:
                drugs = {}
                drugs_pos = line[0].split('.')
                for drug in drugs_pos:
                    drug_name, drug_quant = drug.split(',')
                    drugs[drug_name] = int(drug_quant)

                period = int(line[1])
                client_name = line[2]
                address = line[3]
                phone = line[4]
                id = line[5]
                orders.append((drugs, period, client_name, address, phone, id))
        return orders

    def __generate_client_orders(self):
        orders_list = []
        generated_info_list = self.randomizer.start_new_day()
        for meta, card_id, drugs_ids in generated_info_list:
            drugs = {}
            for drug_id, drug_num in drugs_ids.items():
                drugs[self.__drugs_names[drug_id]] = drug_num
            orders_list.append(ClientOrder(meta, card_id, drugs))
        return orders_list

    def start_next_day(self):
        if self.cur_day < self.n_days:
            delivered_drugs = []
            while self.pharmacy_orders_queue != [] and self.pharmacy_orders_queue[0][0] == self.cur_day:
                delivered_order = self.pharmacy_orders_queue.pop(0)[1]
                delivered_drugs.append(delivered_order.drug)
            self.pharmacy.deliver_drugs(delivered_drugs)

            orders = self.__generate_client_orders()
            self.pharmacy.new_day(orders)

            pharmacy_orders = self.pharmacy.get_drugs_orders()
            for order in pharmacy_orders:
                delivery_date = self.cur_day + self.randomizer.generate_waiting_time()
                self.pharmacy_orders_queue.append((delivery_date, order))
            self.pharmacy_orders_queue = sorted(self.pharmacy_orders_queue, key=lambda x: x[0])

            over_prices = self.pharmacy.get_prices()
            self.randomizer.update_profits(over_prices)

            stats = self.pharmacy.get_statistic()
            self.GUI.show_tmp_statistic(stats)

            self.cur_day += 1
        else:
            final_stats = self.pharmacy.get_final_stats()
            self.GUI.show_final_statistic(final_stats)


class PharmacyOrder:
    def __init__(self, drug):
        self.drug = drug


class DailyStat:
    def __init__(self):
        self.drugs_at_store = {}
        self.courier_max_cap = 0
        self.today_delivered = 0
        self.delivered_orders = []


class FinalStat:
    def __init__(self):
        self.total_profit = 0
        self.total_lost = 0
        self.courier_max_cap = 0
        self.delivered_history = []


class Pharmacy:
    def __init__(self, names, base_prices, profits, quant, lifes, recurring_params):
        self.__drug_info_list = {}
        for drug_info in zip(names, base_prices, profits, quant, lifes):
            self.__drug_info_list[drug_info[0]] = DrugInfo(drug_info)

        self.__drug_store = {}  # dict(drug_name;DrugBatchList)
        self.__waiting_to_store = []
        self.__cur_day = 0
        self.__init_store()

        self.__big_order_thre = 1000
        self.__big_order_sale = 0.03
        self.__loyal_sale = 0.05
        self.__card_sale = None
        self.__max_sale = 0.09

        self.__couriers = None
        self.__max_courier_orders = 7
        self.__courier_max_cap = None
        self.__delivered_history = []

        self.__min_quant_to_reorder = None
        self.__recurring_orders = []
        self.__init_recurring_orders(recurring_params)

        self.__orders_from_pharmacy = None
        self.__stats = None
        self.__lost_shelf_life = 0
        self.__total_profit = 0

    def init_user_params(self, couriers, card_sale, quant_to_reorder):
        self.__couriers = couriers
        self.__card_sale = card_sale
        self.__min_quant_to_reorder = quant_to_reorder
        self.__courier_max_cap = self.__couriers * self.__max_courier_orders

    def __init_store(self):
        for drug_info in self.__drug_info_list.items():
            name = drug_info[0]
            quant = drug_info[1].standard_quantity
            valid_to = self.__cur_day+drug_info[1].shelf_life
            self.__drug_store[name] = [DrugBatch(name, quant, valid_to)]

    def __init_recurring_orders(self, params_list):
        # drugs;period;client;address;phone;id
        for params in params_list:
            meta = params[2:-1]
            card_id = params[-1]
            period = params[1]
            drugs = params[0]
            self.__recurring_orders.append(RecurringOrder(meta, card_id, drugs, period))

    def get_prices(self):
        prof = []
        for drug_info in self.__drug_info_list.values():
            prof.append(drug_info.cur_profit)
        return prof

    def new_day(self, client_orders):
        # todo ret: stats, out_orders, new_prices
        self.__stats = DailyStat()
        self.__stats.courier_max_cap = self.__courier_max_cap
        queue = client_orders[:]
        today_delivered = 0
        self.__cur_day += 1

        queue += self.__proc_recurring_orders()

        orders_to_deliver = self.__process_orders(queue)
        while today_delivered < len(orders_to_deliver) and today_delivered < self.__courier_max_cap:
            orders_to_deliver[today_delivered].if_delivered = True
            self.__total_profit += orders_to_deliver[today_delivered].total_profit
            today_delivered += 1

        self.__delivered_history.append(today_delivered)
        self.__stats.today_delivered = today_delivered
        self.__stats.delivered_orders = orders_to_deliver[:today_delivered]
        orders_form_pharmacy, add_sale, remove_sale, stats_from_store = self.__check_store()
        self.__orders_from_pharmacy = orders_form_pharmacy
        self.__stats.drugs_at_store = stats_from_store
        self.__update_prices(add_sale, remove_sale)

    def __proc_recurring_orders(self):
        orders = []
        for order in self.__recurring_orders:
            if order.last_order is None or self.__cur_day - order.last_order >= order.period:
                order.last_order = self.__cur_day
                orders.append(order.get_client_order())
        return orders

    def get_drugs_orders(self):
        ret = self.__orders_from_pharmacy
        self.__orders_from_pharmacy = None
        return ret

    def deliver_drugs(self, drug_names):
        for drug in drug_names:
            shelf_life = self.__drug_info_list[drug].shelf_life
            standard_quantity = self.__drug_info_list[drug].standard_quantity
            new_batch = DrugBatch(drug, standard_quantity, shelf_life+self.__cur_day)
            self.__drug_store[drug].append(new_batch)
            self.__waiting_to_store.remove(drug)

    def get_statistic(self):
        return self.__stats

    def get_final_stats(self):
        stat = FinalStat()
        stat.delivered_history = self.__delivered_history
        stat.courier_max_cap = self.__courier_max_cap
        stat.total_profit = self.__total_profit
        stat.total_lost = self.__lost_shelf_life
        return stat

    def __update_prices(self, decrease_drugs, increase_drugs):
        # decrease prices
        for drug in decrease_drugs:
            drug_info = self.__drug_info_list[drug]
            drug_info.cur_price = (drug_info.base_price * drug_info.base_profit) / 2
            drug_info.cur_profit = drug_info.cur_price / drug_info.base_price
        # increase prices
        for drug in increase_drugs:
            drug_info = self.__drug_info_list[drug]
            drug_info.cur_price = drug_info.base_price * drug_info.base_profit
            drug_info.cur_profit = drug_info.base_profit

    def __process_orders(self, orders):
        ready_orders = []
        for order in orders:
            order_base_income = 0
            order_cur_income = 0
            order_sale = 0.0
            for drug in order.drugs.items():
                avail_num = self.__get_drug_from_store(drug[0], drug[1])
                if avail_num > 0:
                    drug_name = drug[0]
                    base_price = self.__drug_info_list[drug_name].base_price
                    cur_price = self.__drug_info_list[drug_name].cur_price
                    order_base_income += avail_num * base_price
                    order_cur_income += avail_num * cur_price

                    order.ready_drugs[drug_name] = avail_num

            if order.card_id:
                order_sale += self.__card_sale
            elif order_cur_income > self.__big_order_thre:
                order_sale += self.__big_order_sale
            if order.loyal_client:
                order_sale = min(self.__max_sale, order_sale+self.__loyal_sale)

            order_cur_income -= order_cur_income * order_sale
            order.total_profit = (order_cur_income - order_base_income)

            if order_cur_income != 0:
                ready_orders.append(order)
        return ready_orders

    def __check_store(self):
        add_sale_names = []
        remove_sale_names = []
        pharmacy_orders = []
        drugs_quant = {}

        for drug_on_store in self.__drug_store.items():
            drug_name = drug_on_store[0]
            drug_batches = drug_on_store[1]
            base_price = self.__drug_info_list[drug_name].base_price
            # today was the last day
            while drug_batches and drug_batches[0].valid_to == self.__cur_day-1:
                self.__lost_shelf_life += drug_batches[0].quantity * base_price
                drug_batches.pop(0)
            if drug_batches and drug_batches[0].valid_to - self.__cur_day <= 29:
                drug_info = self.__drug_info_list[drug_name]
                if drug_info.cur_price == drug_info.base_price * drug_info.base_profit:
                    add_sale_names.append(drug_name)
            if drug_batches == [] or drug_batches[0].valid_to - self.__cur_day > 29:
                drug_info = self.__drug_info_list[drug_name]
                if drug_info.cur_price < drug_info.base_price * drug_info.base_profit:
                    remove_sale_names.append(drug_name)
            drug_sum = 0
            for drug_batch in drug_batches:
                drug_sum += drug_batch.quantity
            if drug_name not in self.__waiting_to_store and drug_sum <= self.__min_quant_to_reorder:
                pharmacy_orders.append(PharmacyOrder(drug_name))
                self.__waiting_to_store.append(drug_name)
            drugs_quant[drug_name] = drug_sum

        return pharmacy_orders, add_sale_names, remove_sale_names, drugs_quant

    def __get_drug_from_store(self, name, needed):
        total = 0
        drug_batch_list = self.__drug_store[name]
        while drug_batch_list and total < needed:
            cur_batch = drug_batch_list[0]
            from_cur_batch = min(needed-total, cur_batch.quantity)
            if from_cur_batch == cur_batch.quantity:
                drug_batch_list.pop(0)
            else:
                cur_batch.quantity -= from_cur_batch
            total += from_cur_batch
        return total


if __name__ == '__main__':
    drugs_file = 'drugs.txt'
    orders_file = 'reccuring.txt'

    gui = GUI('GUI', 'org.beeware.gui')
    randomizer = Randomizer
    env = Env(GUI=gui, randomizer_cls=randomizer, drugs_file=drugs_file, orders_file=orders_file)
    gui.init_env(env)
    gui.main_loop()
