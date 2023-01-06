import numpy
import scipy

import arrangeData


column = arrangeData.mcol
row = arrangeData.mrow 


class SupportVectorMachines:
    def __init__(self, C, mode, pT, gamma, k, d=2):
        self.C = C
        self.mode = mode
        self.pT = pT
        self.d = d
        self.gamma = gamma
        self.k = k
        self.w_start = None
        self.H = None
    
    def train(self, DTR, LTR):
        DTRext = numpy.vstack([DTR, numpy.ones((1, DTR.shape[1]))])
        
        DTR0 = DTR[:, LTR==0]
        DTR1 = DTR[:, LTR==1]
        nF = DTR0.shape[1]
        nT = DTR1.shape[1]
        emp_prior_F = (nF / DTR.shape[1])
        emp_prior_T =  (nT / DTR.shape[1])
        Cf = self.C * self.pT 
        Cf = Cf / emp_prior_F
        Ct = self.C * self.pT 
        Ct = Ct / emp_prior_T
    
        Z = numpy.zeros(LTR.shape)
        Z[LTR == 0] = -1
        Z[LTR == 1] = 1
        
        if self.mode == "Linear":
            DTRext = numpy.vstack([DTR, numpy.ones((1,DTR.shape[1]))])
            H = numpy.dot(DTRext.T, DTRext)
            H = column(Z) * row(Z) * H
        elif self.mode == "Quadratic":
            kernel = (numpy.dot(DTRext.T, DTRext)+self.C) ** self.d  + self.k*self.k
            H = column(Z) * row(Z) * kernel
        elif self.mode == "RBF":
            Dist = column((DTR ** 2).sum(0)) + row((DTR ** 2).sum(0)) - 2 * numpy.dot(DTR.T, DTR)
            kernel = numpy.exp(-self.gamma * Dist) + (self.k ** 2)
            H = column(Z) * row(Z) * kernel
        
        self.H = H
            

        #FOR CLASS BALANCING
        C1 = (self.C * self.pT) / (DTR[:, LTR == 1].shape[1] / DTR.shape[1])
        C0 = (self.C * (1 - self.pT)) / (DTR[:, LTR == 0].shape[1] / DTR.shape[1])
        bounds = [((0, C0) if x == 0 else (0, C1)) for x in LTR.tolist()]
       
        alpha_star, x, y = scipy.optimize.fmin_l_bfgs_b(
            self._LDual, 
            numpy.zeros(DTR.shape[1]),
            #bounds = [(0, self.C)] * DTR.shape[1], #no class balancing
            bounds = bounds, #class balancing
            factr = 1e7,
            maxiter = 100000,
            maxfun = 100000
                )

        self.w_star = numpy.dot(DTRext, column(alpha_star) * column(Z))
    
    def compute_scores(self, DTE):
        DTEext = numpy.vstack([DTE, numpy.ones((1, DTE.shape[1]))])
        S = numpy.dot(self.w_star.T, DTEext)
        return S
        
    def _JDual(self, alpha):
        Ha = numpy.dot(self.H, column(alpha))
        aHa = numpy.dot(row(alpha), Ha)
        a1 = alpha.sum()
        return -0.5 * aHa.ravel() + a1, -Ha.ravel() + numpy.ones(alpha.size)
    
    def _LDual(self, alpha):
        loss, grad = self._JDual(alpha)
        return -loss, -grad
    
    def _JPrimal(self, DTRext, w, Z):
        S = numpy.dot(row(w), DTRext)
        loss = numpy.maximum(numpy.zeros(S.shape), 1-Z*S).sum()
        return 0.5*numpy.linalg.norm(w)**2 + self.C*loss