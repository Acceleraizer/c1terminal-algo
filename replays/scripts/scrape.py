import requests
import json
import pickle

class TerminalScraper:

    def __init__(self, replay_file_number = 0):
        self.replay_file_number = replay_file_number

    def get_matches(self, algo_id):
        '''
        input: 
            algo_id: str
        output:
            matches of that algorithm: list[dict]
        '''
        matches_request = requests.get(f'https://terminal.c1games.com/api/game/algo/{algo_id}/matches').text
        matches = json.loads(matches_request)['data']['matches']
        return matches

    def save_matches(self, matches, folder_name = ''):
        '''
        input: 
            matches: list[dict]
            folder_name: str
        output:
            saves the matches into a folder: None
        '''
        match_ids = [game['id'] for game in matches]
        for match_id in match_ids:
            print('saving match: ', match_id)
            with open(f'{folder_name}/{self.replay_file_number}.replay', 'w') as f:
                match_replay = requests.get(f'https://terminal.c1games.com/api/game/replayexpanded/{match_id}').text
                f.write(match_replay)
            self.replay_file_number += 1

    def crawl_dfs(self, stack, visited = set(), n = 50):
        '''
        input: 
            stack: list[str] (list of algorithm ids to try next)
            visited: set{str} (set of visited algorithm ids)
            n: int (number of algorithm ids we should crawl for)
        output:
            updated stack after n iterations of dfs: list[str]
            updated visited after n iterations of dfs: set{str}
        '''
        while stack and n > 0:
            alg_id = stack.pop()
            if alg_id in visited:
                continue
            visited.add(alg_id)
            n -= 1
            print('visiting', alg_id)
            alg_matches = self.get_matches(alg_id)
            for match in alg_matches:
                if not match['winning_algo']['id'] in visited:
                    stack.append(match['winning_algo']['id']) 
                if not match['losing_algo']['id'] in visited:
                    stack.append(match['losing_algo']['id'])  
        return stack, visited

# Example use case
# if __name__ == "__main__":
#     scraper = TerminalScraper()
#     to_visit, visited = scraper.crawl_dfs([245408], n = 4) # Crawl starting from id = 245408 and get 4 ids
#     for algo_id in visited: # Save all the matches of each algorithm
#         scraper.save_matches(scraper.get_matches(algo_id), folder_name = 'replays')

if __name__ == "__main__":
    scraper = TerminalScraper()
    to_visit =  {245257, 245258, 245259, 245260, 245261, 245262, 245263, 245264, 245265, 245266, 245267, 245268, 245269, 245270, 245271, 245272, 245273, 245274, 245275, 245276, 245277, 245278, 245279, 245280, 245281, 245282, 245283, 245284, 245285, 245286, 245287, 245288, 245289, 245290, 245291, 245292, 245293, 245294, 245295, 245300, 245302, 245303, 245304, 245306, 245307, 245308, 245309, 245310, 245312, 245313, 245314, 245315, 245316, 245317, 245318, 245319, 245320, 245321, 245323, 245324, 245325, 245326, 245327, 245328, 245329, 245332, 245338, 245339, 245342, 245343, 245345, 245346, 245347, 245348, 245349, 245351, 245352, 245354, 245355, 245357, 245358, 245359, 245360, 245361, 245362, 245363, 245368, 245369, 245371, 245373, 245374, 245376, 245378, 245380, 245381, 245383, 245385, 245386, 245387, 245388, 245391, 245392, 245393, 245395, 245396, 245397, 245399, 245401, 245403, 245404, 245405, 245407, 245408, 245411, 245412, 245413, 245414, 245415, 245416, 245417, 245418, 245419, 245420, 245421, 245422, 245423, 245424, 245425, 245426, 245427, 245428, 245429, 245430, 245431, 245432, 245433, 245434, 245435, 245437, 245438, 245439, 245440, 245441, 245442, 245443, 245444, 245445, 245446, 245447, 245448, 245449, 245450, 245451, 245452, 245453, 245454, 245455, 245456, 245457, 245458, 245459, 245460, 245461, 245462, 245463, 245464, 245465, 245466, 245467, 245468, 245469, 245470, 245471, 245472, 245473, 245474, 245475, 245476, 245477, 245478, 245479, 245480, 245481, 245482, 245483, 245484, 245105, 245106, 245107, 245108, 245109, 245110, 245111, 245113, 245114, 245115, 245116, 245117, 245118, 245119, 245120, 245121, 245122, 245123, 245125, 245126}
    for algo_id in to_visit:
        scraper.save_matches(scraper.get_matches(algo_id), folder_name = 'replays')

