# Git Strategy for Sequential Labs

This plan outlines a Git workflow for a university course where labs build on top of each other sequentially. The goal is to preserve a snapshot of each lab for grading/reference while allowing the codebase to evolve linearly without merge conflicts or concurrent feature divergence.

## User Review Required
>
> [!IMPORTANT]
> Please review the two proposed strategies below and let me know which one you prefer. **Strategy 1** is highly recommended for software engineering courses as it mimics standard industry practice (Feature Branching), while **Strategy 2** is simpler if you want to avoid branches entirely.

---

## Proposed Strategies

### Strategy 1: Sequential Feature Branches (Recommended)

In this strategy, the `main` branch acts as the "stable" version of your project. You create a new branch for each lab, do your work, and then merge it back into `main` when the lab is finished.

**The Workflow:**

1. **Start Lab 1:** You are on `main`. Create a new branch:

   ```bash
   git checkout -b lab-01
   ```

2. **Work on Lab 1:** Make commits as usual (`git add .`, `git commit -m "..."`).
3. **Submit Lab 1:** Push the `lab-01` branch to GitHub.
4. **Merge to Main:** Once submitted, merge your work into the main branch:

   ```bash
   git checkout main
   git merge lab-01
   ```

5. **Start Lab 2:** Now that `main` has all of Lab 1's code, branch off for Lab 2:

   ```bash
   git checkout -b lab-02
   ```

**Why this is good:** The `lab-01` branch freezes exactly what you submitted for Lab 1. If your instructor needs to see Lab 1, they look at that branch. If you mess up Lab 2, Lab 1 is safely preserved.

---

### Strategy 2: Linear Mainline with Tags (The "No Branches" Approach)

If you do not want to deal with branches at all, you can do all your work linearly on the `main` branch and use Git **Tags** to mark the exact moment a lab is finished.

**The Workflow:**

1. **Work on Lab 1:** Just stay on `main`. Make commits as usual.
2. **Submit Lab 1:** When you are completely done, create a tag:

   ```bash
   git tag -a lab-01-submission -m "Final code for Lab 1"
   git push origin main --tags
   ```

3. **Start Lab 2:** Just keep working on `main` and making new commits. The tag acts as a permanent bookmark to your Lab 1 code.

**Why this is good:** It is incredibly simple. There is only ever one branch. The tags act as snapshots you can always jump back to if needed.

---

## Verification Plan

Once you select a strategy, I can write a quick alias or shell script in your `.bashrc` (if you want) to automate creating and wrapping up labs, or we can just stick to these commands as you progress through the term.

To verify, you will simply check `git log --graph --oneline` at the end of each lab to ensure your history remains perfectly linear.
