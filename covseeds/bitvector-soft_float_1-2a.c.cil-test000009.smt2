(set-logic QF_AUFBV )
(declare-fun ea () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun eb () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun ma () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun mb () (Array (_ BitVec 32) (_ BitVec 8) ) )
(assert (let ( (?B1 (concat  (select  ma (_ bv3 32) ) (concat  (select  ma (_ bv2 32) ) (concat  (select  ma (_ bv1 32) ) (select  ma (_ bv0 32) ) ) ) ) ) (?B2 (concat  (select  mb (_ bv3 32) ) (concat  (select  mb (_ bv2 32) ) (concat  (select  mb (_ bv1 32) ) (select  mb (_ bv0 32) ) ) ) ) ) (?B3 ((_ sign_extend 24)  (select  ea (_ bv0 32) ) ) ) ) (and  (and  (and  (and  (and  (and  (and  (=  false (=  (_ bv0 32) ?B1 ) ) (bvult  ?B1 (_ bv16777216 32) ) ) (=  false (bvsle  ?B3 (_ bv4294967168 32) ) ) ) (bvult  (bvshl  ?B1 (_ bv1 32) ) (_ bv16777216 32) ) ) (bvsle  (bvadd  (_ bv4294967295 32) ?B3 ) (_ bv4294967168 32) ) ) (=  false (=  (_ bv0 32) ?B2 ) ) ) (bvult  ?B2 (_ bv16777216 32) ) ) (bvsle  ((_ sign_extend 24)  (select  eb (_ bv0 32) ) ) (_ bv4294967168 32) ) ) ) )
(check-sat)
(exit)
