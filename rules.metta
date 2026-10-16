; ============================================================
; Glass Jury - rules. All reasoning happens here, in MeTTa.
; ============================================================

; ---- Jury settings (data, so a juror can change them) ----
(weight theme-fit 3)
(weight message 2)
(weight provenance 2)
(weight originality 2)
(threshold select 20)

(criterion theme-fit)
(criterion message)
(criterion provenance)
(criterion originality)

(level high 3)
(level medium 2)
(level low 1)

; ---- Hard gates: a failed or unverifiable gate sends a work to
;      "needs-review". The agent never auto-rejects. ----
(active-gate consent)
(active-gate ai-disclosure)
(active-gate rights)

; True when NO fact of kind $f exists for artwork $a (a gap in the record)
(= (no-fact $a $f) (unify &self ($f $a $v) Empty True))

; (violates $a $gate) returns a gate STATE, or nothing if the gate passes:
;   failed     = the record says something bad
;   no-record  = the record says nothing, so it cannot be verified
(= (violates $a consent)       (match &self (consent $a missing) failed))
(= (violates $a consent)       (let True (no-fact $a consent) no-record))

(= (violates $a ai-disclosure) (match &self (, (ai-used $a yes) (ai-disclosed $a no)) failed))
(= (violates $a ai-disclosure) (let True (no-fact $a ai-used) no-record))
(= (violates $a ai-disclosure) (match &self (ai-used $a yes)
                                 (let True (no-fact $a ai-disclosed) no-record)))

(= (violates $a rights)        (match &self (rights $a unknown) failed))
(= (violates $a rights)        (let True (no-fact $a rights) no-record))

(= (gate-fail $a $g)
   (match &self (active-gate $g) (let $x (violates $a $g) $g)))

(= (unknown-gate $a $g)
   (match &self (active-gate $g) (let no-record (violates $a $g) $g)))

; ---- Weighted criteria ----
; points = weight x level value
(= (crit $a $c)
   (let* (($w (match &self (weight $c $w) $w))
          ($l (match &self ($c $a $l) $l))
          ($v (match &self (level $l $v) $v)))
     (* $w $v)))

(= (contrib $a) (let $c (match &self (criterion $c) $c) (crit $a $c)))

(= (score $a)
   (let $items (collapse (contrib $a))
     (foldl-atom $items 0 $acc $x (+ $acc $x))))

; ---- Gaps: criteria with no data, and criteria rated low ----
(= (missing $a)
   (let $c (match &self (criterion $c) $c)
     (unify &self ($c $a $v) Empty $c)))

(= (weak $a) (let $c (match &self (criterion $c) $c)
               (match &self ($c $a low) $c)))

; ---- Verdict ----
(= (verdict $a)
   (if (== (collapse (gate-fail $a $g)) ())
       (if (>= (score $a) (match &self (threshold select $t) $t))
           selected
           not-selected)
       needs-review))

; Confidence drops when a criterion or a gate fact is missing
(= (confidence $a)
   (if (and (== (collapse (missing $a)) ())
            (== (collapse (unknown-gate $a $g)) ()))
       high
       reduced))

; ---- Plain-language reasons (the words shown in the trace) ----
(reason consent       failed    "Consent is marked as missing for this work")
(reason consent       no-record "No consent information was provided, so consent is unverified")
(reason ai-disclosure failed    "AI was used but not disclosed")
(reason ai-disclosure no-record "AI use or its disclosure was not recorded, so it is unverified")
(reason rights        failed    "Rights holder is unknown")
(reason rights        no-record "No rights information was provided, so rights are unverified")

(outcome-text selected     "No hard gate failed and the score reaches the threshold")
(outcome-text not-selected "No hard gate failed, but the score is below the threshold")
(outcome-text needs-review "A hard gate failed or could not be verified, so a human decides")

; ---- EXPLAIN: the whole reasoning trail, produced by MeTTa itself ----
; (why $a) returns one atom per fact in the trail:
;   (gate <gate> <state> "reason")   (points <criterion> <n>)
;   (gap <criterion>)                (weak-spot <criterion>)
;   (total <score>)  (threshold <n>) (conf <level>)  (outcome <verdict> "reason")
(= (why $a)
   (match &self (active-gate $g)
     (let $s (violates $a $g)
       (match &self (reason $g $s $t) (gate $g $s $t)))))

(= (why $a)
   (let $c (match &self (criterion $c) $c)
     (let $p (crit $a $c) (points $c $p))))

(= (why $a) (let $c (missing $a) (gap $c)))
(= (why $a) (let $c (weak $a) (weak-spot $c)))
(= (why $a) (let $s (score $a) (total $s)))
(= (why $a) (let $t (match &self (threshold select $t) $t) (threshold $t)))
(= (why $a) (let $c (confidence $a) (conf $c)))
(= (why $a)
   (let $v (verdict $a)
     (match &self (outcome-text $v $t) (outcome $v $t))))