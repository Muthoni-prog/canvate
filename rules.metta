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
;      "needs-review". A gate never auto-rejects. ----
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

; A missing criterion is never guessed. Instead we ask: if the gap were
; filled in at the BEST level, would the verdict change? (gap-potential)
; is the most extra points the gaps could still add.
(= (gap-pts $a)
   (let $c (missing $a)
     (let* (($w (match &self (weight $c $w) $w))
            ($v (match &self (level high $v) $v)))
       (* $w $v))))

(= (gap-potential $a)
   (let $items (collapse (gap-pts $a))
     (foldl-atom $items 0 $acc $x (+ $acc $x))))

(= (threshold-value) (match &self (threshold select $t) $t))

; margin = score - threshold. Positive: above the bar. Negative: short of it.
(= (margin $a) (- (score $a) (threshold-value)))

; ---- Machine verdict ----
;  1. a failed or unverifiable gate          -> needs-review
;  2. score reaches the threshold            -> selected
;  3. score short, but gaps COULD close it   -> needs-review (a human should look)
;  4. score short and gaps cannot close it   -> not-selected
(= (verdict-given $a $s)
   (if (== (collapse (gate-fail $a $g)) ())
       (if (>= $s (threshold-value))
           selected
           (if (>= (+ $s (gap-potential $a)) (threshold-value))
               needs-review
               not-selected))
       needs-review))

(= (verdict $a) (let $s (score $a) (verdict-given $a $s)))

; Why a work went to a human: a gate, or a gap that could change the result
(= (review-cause $a)
   (if (== (collapse (gate-fail $a $g)) ()) gap gate))

; ---- Human decision (the juror's challenge to a single verdict) ----
; A human decision is just an atom: (override <artwork> <verdict> "reason").
; It never changes the machine verdict. It only sets the FINAL decision.
(= (final-of $a $v)
   (let $o (collapse (match &self (override $a $v2 $r) $v2))
     (if (== $o ()) $v (car-atom $o))))

(= (final $a) (let $v (verdict $a) (final-of $a $v)))

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
(review-text gate "A hard gate failed or could not be verified, so a human decides")
(review-text gap  "No hard gate failed, but a missing fact could change the result, so a human decides")

(= (outcome-line $a $v)
   (if (== $v needs-review)
       (let $c (review-cause $a) (match &self (review-text $c $t) $t))
       (match &self (outcome-text $v $t) $t)))

; ============================================================
; TRUST FEATURES: where is a verdict fragile, and is a human
; decision consistent with the rules?
; ============================================================
(direction 1)
(direction -1)

; One rating step on one criterion, up (1) or down (-1).
; Returns (candidate <criterion> <from> <to> <points change>).
(= (step-change $a $c $d)
   (let* (($l (match &self ($c $a $l) $l))
          ($v (match &self (level $l $v) $v))
          ($n (+ $v $d))
          ($nl (match &self (level $nl $n) $nl))
          ($w (match &self (weight $c $w) $w))
          ($dl (* $w $d)))
     (candidate $c $l $nl $dl)))

; The single rating steps that would CROSS the threshold, given score $s.
; Only for works whose hard gates are clear (otherwise the score is not
; what decides the verdict). A work with any such step is a "close call".
(= (flips-given $a $s $t)
   (if (== (collapse (gate-fail $a $g)) ())
       (let $d (match &self (direction $d) $d)
         (let $c (match &self (criterion $c) $c)
           (let (candidate $cc $l $nl $dl) (step-change $a $c $d)
             (if (== (>= $s $t) (>= (+ $s $dl) $t))
                 (empty)
                 (flip $cc $l $nl $dl)))))
       (empty)))

; Consistency check on a human decision. Flag any work the machine did NOT
; select that scores HIGHER than a work the human selected.
(= (precedent-gap $a)
   (match &self (override $a selected $r)
     (let $b (match &self (artwork $b) $b)
       (if (== (final $b) not-selected)
           (if (> (score $b) (score $a)) $b (empty))
           (empty)))))

; A human selected a work whose hard gate failed or could not be verified.
(= (overruled $a)
   (match &self (override $a selected $r) (gate-fail $a $g)))

; ---- EXPLAIN: the whole reasoning trail, produced by MeTTa itself ----
; (why $a) returns one atom per fact in the trail:
;   (gate <gate> <state> "reason")   (points <criterion> <n>)
;   (gap <criterion>)                (weak-spot <criterion>)
;   (total <score>)  (threshold <n>) (margin-pts <n>)
;   (best-case <n>)                  only when a gap could still add points
;   (flip <criterion> <from> <to> <points>)  one rating step that changes the verdict
;   (conf <level>)   (outcome <verdict> "reason")
;   (override <verdict> "reason")    only when a human decided
;   (final-verdict <verdict>)
;   (precedent-conflict <artwork>)   a higher-scoring work was not selected
;   (gate-overruled <gate>)          a human selected despite a gate
; Trace atoms use names that are NOT rule names, so they are never re-evaluated.
; Expensive values (score, verdict) are computed once per block and shared.
(= (why $a)
   (match &self (active-gate $g)
     (let $s (violates $a $g)
       (match &self (reason $g $s $t) (gate $g $s $t)))))

(= (why $a)
   (let $c (match &self (criterion $c) $c)
     (let $p (crit $a $c) (points $c $p))))

(= (why $a) (let $c (missing $a) (gap $c)))
(= (why $a) (let $c (weak $a) (weak-spot $c)))
(= (why $a) (let $c (confidence $a) (conf $c)))

; score and verdict block: the score is computed ONCE and shared by every
; atom derived from it (total, margin, best case, close-call steps, verdict)
(= (why $a)
   (let $s (score $a)
     (let $t (threshold-value)
       (let $m (- $s $t)
         (let $p (gap-potential $a)
           (let $b (+ $s $p)
             (let $v (verdict-given $a $s)
               (let $o (outcome-line $a $v)
                 (let $f (final-of $a $v)
                   (superpose ((total $s) (threshold $t) (margin-pts $m)
                               (if (> $p 0) (best-case $b) (empty))
                               (flips-given $a $s $t)
                               (outcome $v $o) (final-verdict $f)))))))))))) 

(= (why $a) (match &self (override $a $v $r) (override $v $r)))
(= (why $a) (let $b (precedent-gap $a) (precedent-conflict $b)))
(= (why $a) (let $g (overruled $a) (gate-overruled $g)))
