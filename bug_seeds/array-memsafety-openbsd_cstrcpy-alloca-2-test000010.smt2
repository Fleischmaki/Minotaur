(set-logic QF_AUFBV )
(declare-fun length1 () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun length2 () (Array (_ BitVec 32) (_ BitVec 8) ) )
(declare-fun nondetString () (Array (_ BitVec 32) (_ BitVec 8) ) )
(assert (let ( (?B1 (concat  (select  nondetString (_ bv7 32) ) (concat  (select  nondetString (_ bv6 32) ) (concat  (select  nondetString (_ bv5 32) ) (concat  (select  nondetString (_ bv4 32) ) (concat  (select  nondetString (_ bv3 32) ) (concat  (select  nondetString (_ bv2 32) ) (concat  (select  nondetString (_ bv1 32) ) (select  nondetString (_ bv0 32) ) ) ) ) ) ) ) ) ) ) (and  (and  (and  (and  (bvslt  (concat  (select  length1 (_ bv3 32) ) (concat  (select  length1 (_ bv2 32) ) (concat  (select  length1 (_ bv1 32) ) (select  length1 (_ bv0 32) ) ) ) ) (_ bv1 32) ) (bvslt  (concat  (select  length2 (_ bv3 32) ) (concat  (select  length2 (_ bv2 32) ) (concat  (select  length2 (_ bv1 32) ) (select  length2 (_ bv0 32) ) ) ) ) (_ bv1 32) ) ) (=  false (bvult  (bvadd  (_ bv18446649672479718632 64) ?B1 ) (_ bv8 64) ) ) ) (=  false (bvult  (bvadd  (_ bv18446649672479718624 64) ?B1 ) (_ bv8 64) ) ) ) (bvult  (bvadd  (_ bv18446649672479718584 64) ?B1 ) (_ bv4 64) ) ) ) )
(check-sat)
(exit)