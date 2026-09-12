# Stage 4 — pre-specified analysis (see Concept Note section 7)
suppressMessages({library(lme4); library(dplyr); library(readr); library(irr); library(emmeans)})
d <- read_csv("runs/closed_scored.csv", show_col_types = FALSE) %>%
  mutate(across(c(lang, strategy, model), factor), correct = as.integer(correct))
d$lang <- relevel(d$lang, ref = "en")

# Descriptive: accuracy with Wilson CI
desc <- d %>% group_by(lang, strategy, model) %>%
  summarise(n = n(), k = sum(correct, na.rm = TRUE), .groups = "drop") %>%
  rowwise() %>% mutate(acc = k/n, lo = prop.test(k, n)$conf.int[1], hi = prop.test(k, n)$conf.int[2])
write_csv(desc, "runs/table_accuracy.csv")

# Primary model: mixed logistic, random intercept for case
m1 <- glmer(correct ~ lang * strategy + model + (1 | case_id), data = d, family = binomial,
            control = glmerControl(optimizer = "bobyqa"))
print(summary(m1))
# Language gap as adjusted risk difference (marginal means on the response scale)
em <- emmeans(m1, ~ lang | strategy, type = "response")
print(em); print(contrast(em, method = "trt.vs.ctrl", ref = "en"))

# Run-to-run consistency (Fleiss kappa across the 3 repeats)
wide <- d %>% select(case_id, lang, strategy, model, rep, choice) %>%
  tidyr::pivot_wider(names_from = rep, values_from = choice)
for (l in levels(d$lang)) {
  w <- wide %>% filter(lang == l) %>% select(`0`, `1`, `2`) %>% as.data.frame()
  cat(l, "Fleiss kappa:", round(kappam.fleiss(w)$value, 3), "\n")
}

# Human-rated open items (after raters return sheets): merge rating_sheet_{lang}.xlsx with rating_key_{lang}.csv
# then fit the same glmer for hallucination and safety_critical_error, and ICC/kappa for inter-rater agreement.
