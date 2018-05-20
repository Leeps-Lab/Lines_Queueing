from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BasePlayer,
    Currency as c, currency_range
)
from otree_redwood.models import Group as RedwoodGroup
from . import config as config_py

'''
Eli Pandolfo <epandolf@ucsc.edu>
otree-redwood>=0.7.0
'''

class Constants(BaseConstants):

    name_in_url = 'Lines_Queueing'
    participation_fee = c(5)

    config = config_py.export_data()
    
    num_rounds = len(config[0])
    players_per_group = len(config[0][0])
    num_players = sum([len(group[0]) for group in config])

    # combined length in seconds players are in the queue room and the payoff room
    # 240 seconds = 4 minutes. There are 2 different rooms players can be in
    # during those 4 minutes, the queue room, where they are not accumulating money,
    # and the payoff room, where they are accumulating money.
    period_length = 140

    alert_messages = {
        'requested': 'You have been requested to swap',
        'requesting': 'You have requested to swap',
        'accepted': 'Your swap request has been accepted',
        'accepting': 'You have accepted a swap request',
        'declined': 'Your swap request has been declined',
        'declining': 'You have declined a swap request',
        'unv_self': 'You must resolve your swap request before requesting again',
        'unv_other': 'You cannot request to swap with this person until they resolve their current swap',
        'next_self': 'You have entered the service room.',
        'next_queue': 'You have advanced one position in the queue',
        'none': ''
    }

# player attributes:
    # - time for all pages
    # - pay rate
    # - position in queue
    # - id in group (what determines a player's starting position in the queue?)
    # - list of transactions that that player has sent/received (this could be 2 lists)

    # time remaining in line and potential payoff should be done all in js
class Player(BasePlayer):

    time_Instructions = models.LongStringField()
    time_Queue = models.LongStringField()
    time_Service = models.LongStringField()
    time_Results = models.LongStringField()

    #bid_price = models.FloatField()
    service_time = models.FloatField() # this is the time it takes them to go thru door once first in line
    pay_rate = models.FloatField()

    trades = models.LongStringField()

class Group(RedwoodGroup):

    group_trades = models.LongStringField()

    def period_length(self):
        return Constants.period_length

    def _on_swap_event(self, event=None, **kwargs):

        #print(event.value)
        for p in self.get_players():

            # relies on only one thing being changed every click, we'll see what happens when two people click at nearly the same time
            # might have to add a timestamp to metadata
            
            # fields 'requesting' and  'accepted' of the person who clicked the button will be updated client-side;
            # all other fields are updated here based on the other fields' states
            # case 1: person is not in_trade and requesting someone who is not in_trade
            # case 2: person is not in_trade and requesting someone who is in_trade
            # case 3: person is in_trade and accepting
            # case 4: person is in_trade and denying
            # Note that the JS will prevent anyone in trade from requesting another trade
            p1 = event.value[str(p.id_in_group)]
            p1['alert'] = Constants.alert_messages['none']
            if p1['next'] == True:
                if p1['pos'] == 0:
                    p1['alert'] = Constants.alert_messages['next_self']
                elif p1['pos'] > 0:
                    p1['alert'] = Constants.alert_messages['next_queue']
                p1['next'] = False
            else:
                if not p1['in_trade'] and p1['requesting'] != None:
                    p2 = event.value[str(p1['requesting'])]
                    if not p2['in_trade']:
                        p1['in_trade'] = True
                        p2['in_trade'] = True
                        p2['requested'] = p1['id']
                        p1['alert'] = Constants.alert_messages['requesting']
                        p2['alert'] = Constants.alert_messages['requested']
                        event.value[str(p1['requesting'])] = p2
                    else:
                        p1['requesting'] = None
                        p1['alert'] = Constants.alert_messages['unv_other']
                elif p1['in_trade']:
                    p2 = event.value[str(p1['requested'])]
                    if p1['accepted'] == 0:
                        p1['in_trade'] = False
                        p2['in_trade'] = False
                        p1['requested'] = None
                        p2['requesting'] = None
                        p1['accepted'] = 2
                        p1['alert'] = Constants.alert_messages['declining']
                        p2['alert'] = Constants.alert_messages['declined']
                    elif p1['accepted'] == 1:
                        p1['in_trade'] = False
                        p2['in_trade'] = False
                        p1['requested'] = None
                        p2['requesting'] = None
                        p1['accepted'] = 2
                        temp = p1['pos']
                        p1['pos'] = p2['pos']
                        p2['pos'] = temp
                        p1['alert'] = Constants.alert_messages['accepting']
                        p2['alert'] = Constants.alert_messages['accepted']
                    event.value[str(p1['requested'])] = p2
            event.value[str(p.id_in_group)] = p1

        # broadcast the updated data out to all subjects
        self.send("swap", event.value)
    

class Subsession(BaseSubsession):
    
    def creating_session(self):
        self.group_randomly()

        for g_index, g in enumerate(self.get_groups()):
            self.session.vars[g_index] = {}
            g_data = Constants.config[g_index][self.round_number - 1]
            for p in g.get_players():
                p.participant.vars['pay_rate'] = g_data[p.id_in_group - 1]['pay_rate']
                p.participant.vars['service_time'] = g_data[p.id_in_group - 1]['service_time']
                p.participant.vars['start_pos'] = p.id_in_group
                p.participant.vars['group'] = g_index
                p_data = {
                    'id': p.id_in_group,
                    'pos': p.participant.vars['start_pos'],
                    'in_trade': False,
                    'requested': None,
                    'requesting': None, # clicking a trade button changes this value
                    'accepted': 2, # 2 is None, 1 is True, 0 is False; clicking a yes/no button changes this value
                    'alert': Constants.alert_messages['none'],
                    'num_players_queue': Constants.num_players,
                    'num_players_service': 0,
                    'next': False,
                    'metadata': None # might move this to be for the whole group, not for every player
                }
                self.session.vars[g_index][p.id_in_group] = p_data


