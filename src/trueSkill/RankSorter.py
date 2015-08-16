



class RankSorter :

#    /**
#     * Performs an in-place sort of the items in according to the score in a decreasing order.
#     * 
#     * @param $items The items to sort according to the order specified by ranks.
#     * @param $scores The score for each item where bigger is better
#     */
    @staticmethod
    def sort(teams, teamScores) :
      
        scores, teams = zip(*sorted(zip(teamScores, teams), reverse=True))
        return scores, teams


