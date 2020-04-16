import numpy as np
import copy
import csv

from GUI import GUI, UserParams


class ClientOrder:
    """structure for client order information"""
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
    """class for repeating orders"""
    def __init__(self, meta, card_id, drugs, period):
        self.__client_order = ClientOrder(meta, card_id, drugs, True)
        self.period = period
        self.last_order = None

    def get_client_order(self):
        """return copy of client order"""
        return copy.deepcopy(self.__client_order)


class DrugInfo:
    """structure for information about drug(for pharmacy class)"""
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
    """class to check shelf-life of the drug on the store"""
    def __init__(self, drug_name, quantity, valid_to):
        self.drug_name = drug_name
        self.valid_to = valid_to
        self.quantity = quantity


class Randomizer:
    """class for generation random orders and"""
    def __init__(self):
        self.__base_prices = []
        self.__profits = []
        self.__average_drugs_in_order = 3
        self.__order_var = 1
        self.__card_proba = 0.3
        self.__max_card_id = 10000
        self.__min_wainting_time = 1
        self.__max_waiting_time = 3
        self.__order_scale = None

    def init_user_params(self, order_scale):
        """initialize parameters from user interface"""
        self.__order_scale = order_scale

    def init_params(self, prices, profits):
        """initialize parameters todo"""
        self.__profits = profits
        self.__base_prices = prices

    def update_profits(self, new_profits):
        """set pharmacy profits for drugs; use them for further generation"""
        self.__profits = new_profits

    def __generate_purchases(self, x):
        """
        generate purchases average num for a drug

        :param list[int,int] x: [drug price, drug markup]
        :return: float average purchases
        """
        price = x[0]
        profit = x[1]
        arg = price * (profit ** 2)
        arg = -np.log(arg) * 2 + 12
        res = self.__order_scale * (np.exp(arg) / (1 + np.exp(arg)))
        return res

    def start_new_day(self):
        """
        generate list of orders parameters for a new day

        :return: List[((str, str, str), int, dict)] - [((name, address, phone_number), card_id, ordered_drugs)]
        """
        average_purchases = np.apply_along_axis(self.__generate_purchases, axis=0,
                                                arr=[self.__base_prices, self.__profits])
        purchase_drugs = np.random.poisson(average_purchases)
        generated_orders_info = []
        while True:
            meta, card_id, ordered_drugs_ids = self.__generate_order_info(purchase_drugs)
            if ordered_drugs_ids:
                generated_orders_info.append((meta, card_id, ordered_drugs_ids))
            else:
                break
        return generated_orders_info

    def __generate_order_info(self, purchase_drugs):
        """
        generate order parameters

        :param list[int] purchase_drugs: average purchase of drugs today
        :return: Tuple((str, str, str), int, dict) - ((name, address, phone_number), card_id, ordered_drugs)
        """
        meta = self.__generate_meta()
        card_id = self.__generate_card_id()
        ordered_drugs_ids = {}
        n_drugs_in_order = round(np.random.normal(self.__average_drugs_in_order, self.__order_var))
        i = 0
        while np.sum(purchase_drugs) != 0 and i < n_drugs_in_order:
            i += 1
            drugs_proba = purchase_drugs / np.sum(purchase_drugs)
            drug_id = np.random.choice(len(self.__base_prices), p=drugs_proba)
            if drug_id in ordered_drugs_ids:
                ordered_drugs_ids[drug_id] += 1
            else:
                ordered_drugs_ids[drug_id] = 1
            purchase_drugs[drug_id] -= 1

        return meta, card_id, ordered_drugs_ids

    def __generate_card_id(self):
        """
        generate random card id or None (with given probability)

        :return: int: card id or None
        """
        if np.random.binomial(1, self.__card_proba):
            return np.random.randint(1, self.__max_card_id)
        return None

    def __generate_meta(self):
        """
        redundant function for pharmacy emulation

        :return: (str, str, str): (name, address, phone_number)
        """
        # todo add true generation
        return 'A', 'B', 'C'

    def generate_waiting_time(self):
        """
        generates random waiting time for new drugs for pharmacy

        :return: int: waiting time (days)
        """
        return round(np.random.uniform(self.__min_wainting_time, self.__max_waiting_time))


class Env:
    """
    class for environment emulation
    """
    def __init__(self, GUI, randomizer_cls, drugs_file, orders_file):
        """
        :param GUI: interface
        :param randomizer_cls: randomizer class
        :param str drugs_file: file with drugs
        :param str orders_file:  file with repeation orders
        """
        self.GUI = GUI
        self.__drugs_names = []
        names, prices, profits, quants, life = self.__load_drugs_info(drugs_file)
        recurring_orders = self.__load_orders_info(orders_file)
        self.randomizer = randomizer_cls()
        self.randomizer.init_params(prices, profits)
        self.pharmacy = Pharmacy(names, prices, profits, quants, life, recurring_orders)

        self.cur_day = 0
        self.n_days = None
        self.order_history = []
        self.pharmacy_orders_queue = []

    def init_user_parameters(self, params):
        """
        init params from user interface

        :param  UserParams params: from gui
        """
        orders_scale = params.orders_scale
        couriers = params.couriers
        card_sale = params.card_sale
        quant_to_reorder = params.quant_to_reorder
        self.n_days = params.n_days
        self.randomizer.init_user_params(orders_scale)
        self.pharmacy.init_user_params(couriers, card_sale, quant_to_reorder)

    def __load_drugs_info(self, filename):
        """
        open and parse file with drug information
        :param str filename:
        :return: Tuple:(List[names], List[prices], List[profits], List[quants], List[lifes])
        """
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
        """load info about repeating orders"""
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
        """for new day generate list of client orders"""
        orders_list = []
        generated_info_list = self.randomizer.start_new_day()
        for meta, card_id, drugs_ids in generated_info_list:
            drugs = {}
            for drug_id, drug_num in drugs_ids.items():
                drugs[self.__drugs_names[drug_id]] = drug_num
            orders_list.append(ClientOrder(meta, card_id, drugs))
        return orders_list

    def __daily_routine(self):
        """do usual daily generations and interact with pharmacy"""
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

        profits = self.pharmacy.get_profits()
        self.randomizer.update_profits(profits)

        stats = self.pharmacy.get_statistic()
        return stats

    def start_next_day(self, no_tmp=False):
        """
        start emulation day by day
        :param bool no_tmp: flag - don't temporary statistic after each day
        """
        if not no_tmp:
            if self.cur_day < self.n_days:
                stats = self.__daily_routine()
                self.GUI.show_tmp_statistic(stats)
                self.cur_day += 1
            else:
                final_stats = self.pharmacy.get_final_stats()
                self.GUI.show_final_statistic(final_stats)
        else:
            for _ in range(self.n_days):
                _ = self.__daily_routine()
                self.cur_day += 1
            final_stats = self.pharmacy.get_final_stats()
            print(final_stats)
            self.GUI.show_final_statistic(final_stats)


class PharmacyOrder:
    """struct: order from pharmacy for more drugs"""
    def __init__(self, drug):
        self.drug = drug


class DailyStat:
    """struct: daily statistics from pharmacy to GUI"""
    def __init__(self):
        self.cur_day = 0
        self.drugs_at_store = {}
        self.courier_max_load = 0
        self.today_delivered = 0
        self.delivered_orders = []


class FinalStat:
    """struct: final statistics after last day from pharmacy to GUI"""
    def __init__(self):
        self.total_profit = 0
        self.total_lost = 0
        self.courier_max_load = 0
        self.delivered_history = []


class Pharmacy:
    """class emulating pharmacy"""
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
        self.__max_courier_orders = 15
        self.__courier_max_load = None
        self.__to_deliver_history = []

        self.__min_quant_to_reorder = None
        self.__recurring_orders = []
        self.__init_recurring_orders(recurring_params)

        self.__orders_from_pharmacy = None
        self.__stats = None
        self.__lost_shelf_life = 0
        self.__total_profit = 0

    def init_user_params(self, couriers, card_sale, quant_to_reorder):
        """init parameters from GUI"""
        self.__couriers = couriers
        self.__card_sale = card_sale
        self.__min_quant_to_reorder = quant_to_reorder
        self.__courier_max_load = self.__couriers * self.__max_courier_orders

    def __init_store(self):
        """initialize store and prepare for emulation run"""
        for drug_info in self.__drug_info_list.items():
            name = drug_info[0]
            quant = drug_info[1].standard_quantity
            valid_to = self.__cur_day+drug_info[1].shelf_life
            self.__drug_store[name] = [DrugBatch(name, quant, valid_to)]

    def __init_recurring_orders(self, params_list):
        """initialize repeating orders and """
        for params in params_list:
            meta = params[2:-1]
            card_id = params[-1]
            period = params[1]
            drugs = params[0]
            self.__recurring_orders.append(RecurringOrder(meta, card_id, drugs, period))

    def get_profits(self):
        """return updated markups"""
        prof = []
        for drug_info in self.__drug_info_list.values():
            prof.append(drug_info.cur_profit)
        return prof

    def new_day(self, client_orders):
        """start new day for pharmacy; do standard actions"""
        self.__stats = DailyStat()
        self.__stats.courier_max_load = self.__courier_max_load
        queue = client_orders[:]
        today_delivered = 0
        self.__cur_day += 1

        queue += self.__proc_recurring_orders()

        orders_to_deliver, drugs_ordered = self.__process_orders(queue)
        while today_delivered < len(orders_to_deliver) and today_delivered < self.__courier_max_load:
            orders_to_deliver[today_delivered].if_delivered = True
            self.__total_profit += orders_to_deliver[today_delivered].total_profit
            today_delivered += 1

        self.__to_deliver_history.append(len(orders_to_deliver))
        self.__stats.cur_day = self.__cur_day
        self.__stats.today_ordered = len(orders_to_deliver)
        self.__stats.today_delivered = today_delivered
        self.__stats.delivered_orders = orders_to_deliver[:today_delivered]
        orders_form_pharmacy, add_sale, remove_sale, stats_from_store = self.__check_store()
        self.__orders_from_pharmacy = orders_form_pharmacy
        new_prices = self.__update_prices(add_sale, remove_sale)
        self.__stats.drugs_info = {item[0]: [item[1], drugs_ordered[item[0]], stats_from_store[item[0]]]
                                   for item in new_prices.items()}

    def __proc_recurring_orders(self):
        """get orders from loyal clients"""
        orders = []
        for order in self.__recurring_orders:
            if order.last_order is None or self.__cur_day - order.last_order >= order.period:
                order.last_order = self.__cur_day
                orders.append(order.get_client_order())
        return orders

    def get_drugs_orders(self):
        """get orders from pharmacy (to deliver more drugs)"""
        ret = self.__orders_from_pharmacy
        self.__orders_from_pharmacy = None
        return ret

    def deliver_drugs(self, drug_names):
        """deliver ordered drugs on pharmacy store"""
        for drug in drug_names:
            shelf_life = self.__drug_info_list[drug].shelf_life
            standard_quantity = self.__drug_info_list[drug].standard_quantity
            new_batch = DrugBatch(drug, standard_quantity, shelf_life+self.__cur_day)
            self.__drug_store[drug].append(new_batch)
            self.__waiting_to_store.remove(drug)

    def get_statistic(self):
        """get daily statistic"""
        return self.__stats

    def get_final_stats(self):
        stat = FinalStat()
        stat.delivered_history = self.__to_deliver_history
        stat.courier_max_load = self.__courier_max_load
        stat.total_profit = self.__total_profit
        stat.total_lost = self.__lost_shelf_life
        return stat

    def __update_prices(self, decrease_drugs, increase_drugs):
        """update prices for drugs after this day"""
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
        return {item[0]: item[1].cur_price for item in self.__drug_info_list.items()}

    def __process_orders(self, orders):
        ready_orders = []
        drugs_ordered = {drug_name:0 for drug_name in self.__drug_info_list.keys()}
        for order in orders:
            order_base_income = 0
            order_cur_income = 0
            order_sale = 0.0
            for drug in order.drugs.items():
                drug_name = drug[0]
                drugs_ordered[drug_name] += drug[1]
                avail_num = self.__get_drug_from_store(drug_name, drug[1])
                if avail_num > 0:
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
        return ready_orders, drugs_ordered

    def __check_store(self):
        """check store for overdue and running/ran out drugs"""
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
        """get needed drugs from store(if possible) old drugs goes first"""
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
