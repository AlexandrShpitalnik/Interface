import toga
from toga.style.pack import *


class GUI(toga.App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = None
        self.cur_couriers_label = None
        self.max_couriers_label = None
        self.drugs_daily_table = None
        self.input_flag = False
        self.start_flag = False
        self.new_day_flag = False
        self.st_window = None

    def init_env(self, env):
        self.env = env

    def create_tmp_stat(self):
        # todo - add button handler
        self.main_window = toga.MainWindow(title='daily stats')

        data = []
        self.drugs_daily_table = toga.Table(headings=['drugs', 'quantity'], data=data)

        right_container = toga.Box()
        right_container.style.update(direction=COLUMN, padding_top=50)

        self.cur_couriers_label = toga.Label('cur couriers ', style=Pack(text_align=RIGHT))
        cur_couriers_box = toga.Box(children=[self.cur_couriers_label])
        cur_couriers_box.style.padding = 50
        right_container.add(cur_couriers_box)
        self.max_couriers_label = toga.Label('max couriers ', style=Pack(text_align=RIGHT))
        max_couriers_box = toga.Box(children=[self.max_couriers_label])
        max_couriers_box.style.padding = 50
        right_container.add(max_couriers_box)

        def next_day_handler(widget):
            self.env.start_next_day()

        button = toga.Button('start new day', on_press=next_day_handler)
        button.style.padding = 100
        button.style.width = 300
        right_container.add(button)

        split = toga.SplitContainer()

        split.content = [self.drugs_daily_table, right_container]

        self.main_window.content = split
        self.main_window.show()

    def show_tmp_statistic(self, stat):

        drug_dict = stat.drugs_at_store
        couriers_max = stat.courier_max_load
        couriers_cur = stat.today_delivered
        orders = stat.delivered_orders
        self.drugs_daily_table.data = list(drug_dict.items())
        self.drugs_daily_table.refresh()

        self.max_couriers_label.text = 'max load '+str(couriers_max)
        self.max_couriers_label.refresh()

        self.cur_couriers_label.text = 'cur load' + str(couriers_cur)
        self.max_couriers_label.refresh()

    def show_final_statistic(self, stat):
        profit = int(stat.total_profit)
        lost = stat.total_lost
        couriers = [c/stat.courier_max_load for c in stat.delivered_history]
        self.st_window = toga.Window(title='final stats')

        self.drugs_daily_table = toga.Table(headings=['couriers'], data=couriers)

        right_container = toga.Box()
        right_container.style.update(direction=COLUMN, padding_top=50)

        self.cur_couriers_label = toga.Label('profit ' + str(profit), style=Pack(text_align=RIGHT))
        cur_couriers_box = toga.Box(children=[self.cur_couriers_label])
        cur_couriers_box.style.padding = 50
        right_container.add(cur_couriers_box)
        self.max_couriers_label = toga.Label('lost ' + str(lost), style=Pack(text_align=RIGHT))
        max_couriers_box = toga.Box(children=[self.max_couriers_label])
        max_couriers_box.style.padding = 50
        right_container.add(max_couriers_box)

        split = toga.SplitContainer()

        split.content = [self.drugs_daily_table, right_container]

        self.st_window.content = split
        self.st_window.show()

    def startup(self):
        self.main_window = toga.MainWindow(title='params')

        main_box = toga.Box()
        main_box.style.update(direction=COLUMN, padding_top=50)

        n_days_label = toga.Label('days', style=Pack(text_align=RIGHT))
        n_days_input = toga.TextInput()
        n_days_box = toga.Box(children=[n_days_input, n_days_label])
        n_days_box.style.update(direction=ROW, padding=5)
        main_box.add(n_days_box)
        prob_card_label = toga.Label('having card probability', style=Pack(text_align=RIGHT))
        prob_card_input = toga.TextInput()
        prob_card_box = toga.Box(children=[prob_card_input, prob_card_label])
        prob_card_box.style.update(direction=ROW, padding=5)
        main_box.add(prob_card_box)
        orders_scale_label = toga.Label('orders scale factor', style=Pack(text_align=RIGHT))
        orders_scale_input = toga.TextInput()
        orders_scale_box = toga.Box(children=[orders_scale_input, orders_scale_label])
        orders_scale_box.style.update(direction=ROW, padding=5)
        main_box.add(orders_scale_box)

        sale_label = toga.Label('sale for card', style=Pack(text_align=RIGHT))
        sale_input = toga.TextInput()
        sale_box = toga.Box(children=[sale_input, sale_label])
        sale_box.style.update(direction=ROW, padding=5)
        main_box.add(sale_box)
        n_couriers_label = toga.Label('couriers', style=Pack(text_align=RIGHT))
        n_couriers_input = toga.TextInput()
        n_couriers_box = toga.Box(children=[n_couriers_input, n_couriers_label])
        n_couriers_box.style.update(direction=ROW, padding=5)
        main_box.add(n_couriers_box)
        n_to_reorder_label = toga.Label('number of drugs to reorder', style=Pack(text_align=RIGHT))
        n_to_reorder_input = toga.TextInput()
        n_to_reorder_box = toga.Box(children=[n_to_reorder_input, n_to_reorder_label])
        n_to_reorder_box.style.update(direction=ROW, padding=5)
        main_box.add(n_to_reorder_box)

        def __start_button_handler(widget):
            class Params:
                pass

            params = Params()

            if not self.input_flag:
                self.input_flag = True

                params.n_days = int(n_days_input.value)
                params.card_proba = float(prob_card_input.value)
                params.orders_scale = float(orders_scale_input.value)
                params.card_sale = float(sale_input.value) / 100.0
                params.couriers = int(n_days_input.value)
                params.quant_to_reorder = int(n_to_reorder_input.value)

                self.env.init_user_parameters(params)
                self.create_tmp_stat()

        button = toga.Button('start emulation', on_press=__start_button_handler)
        button.style.padding = 50
        button.style.flex = 1
        main_box.add(button)

        self.main_window.content = main_box
        self.main_window.show()


def main():
    return GUI('GUI', 'org.beeware.gui')
