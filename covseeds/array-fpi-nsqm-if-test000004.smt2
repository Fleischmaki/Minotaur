(set-logic QF_AUFBV )
(declare-fun N () (Array (_ BitVec 32) (_ BitVec 8) ) )
(assert (let ( (?B1 (concat  (select  N (_ bv3 32) ) (concat  (select  N (_ bv2 32) ) (concat  (select  N (_ bv1 32) ) (select  N (_ bv0 32) ) ) ) ) ) ) (let ( (?B2 ((_ sign_extend 32)  ?B1 ) ) ) (let ( (?B3 (bvmul  (_ bv8 64) ?B2 ) ) ) (and  (and  (and  (and  (=  false (bvsle  ?B1 (_ bv0 32) ) ) (bvule  ?B2 (_ bv536870911 64) ) ) (=  false (=  (_ bv8 64) ?B3 ) ) ) (bvult  (_ bv2147483648 64) ?B3 ) ) (=  false (=  (_ bv2147483656 64) ?B3 ) ) ) ) ) ) )
(check-sat)
(exit)
