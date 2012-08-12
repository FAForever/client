class Teams :
    @staticmethod
    def concat(*args, **kwargs) :

        result = []

        for currentTeam in args :

            localCurrentTeam = currentTeam
            result.append(localCurrentTeam)


        return result

