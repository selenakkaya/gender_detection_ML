import numpy
import scipy
import scipy.special
import arrangeData


mcol = arrangeData.mcol
mrow = arrangeData.mrow 

class GMM_classifier:
    def __init__(self, n, mode, tiedness):
        self.n = n 
        self.gmm_0 = None
        self.gmm_1 = None
        self.mode = mode
        self.tiedness = tiedness
    
    def train(self, D, L):
        self.gmm_0 = self._LBG(D[:, L==0], self.n)
        self.gmm_1 = self._LBG(D[:, L==1], self.n)
    
    def compute_lls(self, DTE):
        ll0 = self._GMM_ll_per_sample(DTE, self.gmm_0)
        ll1 = self._GMM_ll_per_sample(DTE, self.gmm_1)
        return ll0, ll1
    
    def compute_scores(self, DTE):
        ll0, ll1 = self.compute_lls(DTE)
        return ll1-ll0
    
    def _LBG(self, X, doublings):
        
        gmm = [(1.0, mcol(X.mean(1)), numpy.cov(X))]
        for i in range(doublings):
            doubled = []

            for component in gmm:
                w = component[0]
                mu = component[1]
                sigma = component[2]
                
                U, s, Vh = numpy.linalg.svd(sigma)
                d = U[:, 0:1] * s[0]**0.5 * 0.1

                comp_1 = (w/2, mu+d, sigma)
                comp_2 = (w/2, mu-d, sigma)

                doubled.append(comp_1)
                doubled.append(comp_2)


            if self.mode == "full" and self.tiedness == "untied":
                gmm = self._GMM_EM(X, doubled)

            elif self.mode == "naive" and self.tiedness == "untied":
                gmm = self._GMM_EM_diag(X, doubled)

            elif self.mode == "full" and self.tiedness == "tied":
                gmm = self._GMM_EM_tied(X, doubled)

            elif self.mode == "naive" and self.tiedness == "tied":
                gmm = self._GMM_EM_diag_tied(X, doubled)
        return gmm
    
    def _logpdf_GAU_ND_Opt(self, X, mu, C):
        P = numpy.linalg.inv(C)
        const = -0.5 * X.shape[0] * numpy.log(2*numpy.pi)
        const += -0.5 * numpy.linalg.slogdet(C)[1]
        
        Y = []
        for i in range(X.shape[1]):
            x = X[:, i:i+1]
            res = const + -0.5 * numpy.dot((x-mu).T, numpy.dot(P, (x-mu)))
            Y.append(res)
        
        return numpy.array(Y).ravel()

    def _GMM_ll_per_sample(self, X, gmm):
        G = len(gmm)
        N = X.shape[1]
        S = numpy.zeros((G, N))
        
        for g in range(G):
            S[g, :] = self._logpdf_GAU_ND_Opt(X, gmm[g][1], gmm[g][2]) + numpy.log(gmm[g][0])
        return scipy.special.logsumexp(S, axis=0)

    def _GMM_EM(self, X, gmm):
        new_ll = None
        old_ll = None
        G = len(gmm)
        N = X.shape[1]
        
        psi = 0.01
        
        while old_ll is None or new_ll-old_ll>1e-6:
            old_ll = new_ll
            SJ = numpy.zeros((G, N))
            for g in range(G):
                SJ[g, :] = self._logpdf_GAU_ND_Opt(X, gmm[g][1], gmm[g][2]) + numpy.log(gmm[g][0])
            SM = scipy.special.logsumexp(SJ, axis=0)
            new_ll = SM.sum() / N
            P = numpy.exp(SJ - SM)
            
            gmm_new = []
            for g in range(G):
                gamma = P[g, :]
                Z = gamma.sum()
                F = (mrow(gamma)*X).sum(1)
                S = numpy.dot(X, (mrow(gamma)*X).T)
                w = Z/N
                mu = mcol(F/Z)
                sigma = S/Z - numpy.dot(mu, mu.T)
                U, s, _ = numpy.linalg.svd(sigma)
                s[s<psi] = psi
                sigma = numpy.dot(U, mcol(s)*U.T)
                
                gmm_new.append((w, mu, sigma))
            gmm = gmm_new

        return gmm
    
    def _GMM_EM_diag(self, X, gmm):
        new_ll = None
        old_ll = None
        G = len(gmm)
        N = X.shape[1]
        
        psi = 0.01
        
        while old_ll is None or new_ll-old_ll>1e-6:
            old_ll = new_ll
            SJ = numpy.zeros((G, N))
            for g in range(G):
                SJ[g, :] = self._logpdf_GAU_ND_Opt(X, gmm[g][1], gmm[g][2]) + numpy.log(gmm[g][0])
            SM = scipy.special.logsumexp(SJ, axis=0)
            new_ll = SM.sum() / N
            P = numpy.exp(SJ - SM)
            
            gmm_new = []
            for g in range(G):
                gamma = P[g, :]
                Z = gamma.sum()
                F = (mrow(gamma)*X).sum(1)
                S = numpy.dot(X, (mrow(gamma)*X).T)
                w = Z/N
                mu = mcol(F/Z)
                sigma = S/Z - numpy.dot(mu, mu.T)
                #diagonalization
                sigma = sigma * numpy.eye(sigma.shape[0])
                
                U, s, _ = numpy.linalg.svd(sigma)
                s[s<psi] = psi
                sigma = numpy.dot(U, mcol(s)*U.T)
                
                gmm_new.append((w, mu, sigma))
            gmm = gmm_new

        return gmm
    
    def _GMM_EM_tied(self, X, gmm):
        new_ll = None
        old_ll = None
        G = len(gmm)
        N = X.shape[1]
        
        psi = 0.01
        
        while old_ll is None or new_ll-old_ll>1e-6:
            old_ll = new_ll
            SJ = numpy.zeros((G, N))
            for g in range(G):
                SJ[g, :] = self._logpdf_GAU_ND_Opt(X, gmm[g][1], gmm[g][2]) + numpy.log(gmm[g][0])
            SM = scipy.special.logsumexp(SJ, axis=0)
            new_ll = SM.sum() / N
            P = numpy.exp(SJ - SM)
            
            gmm_new = []
            summatory = numpy.zeros((X.shape[0], X.shape[0]))
            for g in range(G):
                gamma = P[g, :]
                Z = gamma.sum()
                F = (mrow(gamma)*X).sum(1)
                S = numpy.dot(X, (mrow(gamma)*X).T)
                w = Z/N
                mu = mcol(F/Z)
                sigma = S/Z - numpy.dot(mu, mu.T)
                summatory += Z*sigma
                gmm_new.append((w, mu, sigma))
            #making it tied
            sigma = summatory / G
            
            #constraint
            U, s, _ = numpy.linalg.svd(sigma)
            s[s<psi] = psi
            sigma = numpy.dot(U, mcol(s)*U.T)
            gmm = gmm_new
        return gmm
    
    def _GMM_EM_diag_tied(self, X, gmm):
        new_ll = None
        old_ll = None
        G = len(gmm)
        N = X.shape[1]
        
        psi = 0.01
        
        while old_ll is None or new_ll-old_ll>1e-6:
            old_ll = new_ll
            SJ = numpy.zeros((G, N))
            for g in range(G):
                SJ[g, :] = self._logpdf_GAU_ND_Opt(X, gmm[g][1], gmm[g][2]) + numpy.log(gmm[g][0])
            SM = scipy.special.logsumexp(SJ, axis=0)
            new_ll = SM.sum() / N
            P = numpy.exp(SJ - SM)
            
            gmm_new = []
            summatory = numpy.zeros((X.shape[0], X.shape[0]))
            for g in range(G):
                gamma = P[g, :]
                Z = gamma.sum()
                F = (mrow(gamma)*X).sum(1)
                S = numpy.dot(X, (mrow(gamma)*X).T)
                w = Z/N
                mu = mcol(F/Z)
                sigma = S/Z - numpy.dot(mu, mu.T)
                #making diagonalize
                sigma = sigma * numpy.eye(sigma.shape[0])
                summatory += Z*sigma
                gmm_new.append((w, mu, sigma))

            sigma = summatory / G
            #constraint
            U, s, _ = numpy.linalg.svd(sigma)
            s[s<psi] = psi
            sigma = numpy.dot(U, mcol(s)*U.T)
            gmm = gmm_new
        return gmm