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

; ---- Hard gates: a failure sends a work to "needs-review", never auto-reject ----
(active-gate consent)
(active-gate ai-disclosure)
(active-gate rights)

(= (violates $a consent)       (match &self (consent $a missing) True))
(= (violates $a ai-disclosure) (match &self (, (ai-used $a yes) (ai-disclosed $a no)) True))
(= (violates $a rights)        (match &self (rights $a unknown) True))

(= (gate-fail $a $g)
   (match &self (active-gate $g) (let $x (violates $a $g) $g)))

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

(= (confidence $a)
   (if (== (collapse (missing $a)) ()) high reduced))

; ---- Plain-language reasons (shown in the trace) ----
(reason consent       "Artist consent is not on record")
(reason ai-disclosure "AI was used but not disclosed")
(reason rights        "Rights holder is unknown")