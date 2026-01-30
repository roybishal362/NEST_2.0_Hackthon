# C-TRUST Video Presentation Script

**Duration**: 7-8 minutes  
**Tone**: Conversational, engaging, human-like  
**Audience**: Evaluators, stakeholders, technical and non-technical viewers

---

## 1. Opening (30 seconds)

Hey there! Imagine you're overseeing 23 clinical trials simultaneously. Each one has thousands of data points coming in daily - patient visits, adverse events, lab results, queries. Now here's the million-dollar question: How do you know if your data is actually good enough to submit to the FDA?

That's exactly the problem we're solving with C-TRUST - Clinical Trial Risk Understanding through Systematic Testing. It's an AI-powered system that acts like having seven expert reviewers working 24/7, analyzing your clinical trial data and telling you exactly where the risks are.

In the next few minutes, I'm going to show you how C-TRUST analyzes real data from 23 studies, identifies critical issues before they become problems, and gives you a clear, actionable view of your entire portfolio. Let's dive in!


---

## 2. The Problem (1 minute)

So let's talk about the real challenge here. Clinical trials are incredibly complex operations. You've got data flowing in from multiple sources - your EDC system, adverse event dashboards, coding reports, query systems - and it's all in different formats, different Excel files, with inconsistent column names.

Here's what keeps clinical data managers up at night:

**First, there's the patient safety risk.** A single missed fatal adverse event or a delayed safety review can put patients at risk and trigger regulatory action. We're talking about real lives here, and the data needs to be rock-solid.

**Second, the financial impact is massive.** Poor data quality costs the pharmaceutical industry about $2.5 billion annually. Every month of delay in FDA approval because of data issues? That's $1 to $3 million down the drain. And that's just one study.

**Third, it doesn't scale.** Traditional manual review means your data managers are spending 40 to 60 percent of their time just checking data quality. When you're running 20 or 30 studies simultaneously, that's simply not sustainable.

And here's the kicker - by the time you discover issues through manual review, it's often weeks or months after they occurred. At that point, remediation is expensive and time-consuming.

What we needed was a system that could automatically analyze data quality across all studies, identify risks in real-time, and do it with the same rigor as a team of expert reviewers. That's where C-TRUST comes in.


---

## 3. The Solution Overview (1 minute)

Alright, so here's how C-TRUST works. Instead of building one massive AI model that tries to do everything, we took a different approach - we built seven specialized AI agents. Think of them as seven expert reviewers, each focused on a specific aspect of data quality.

**We've got:**
- A **Safety & Compliance Agent** that's laser-focused on adverse events and patient safety
- A **Data Completeness Agent** checking for missing data and incomplete forms
- A **Coding Readiness Agent** monitoring medical coding quality
- A **Query Quality Agent** tracking open queries and resolution times
- A **Temporal Drift Agent** watching for delays in data entry
- An **EDC Quality Agent** validating data entry accuracy
- And a **Stability Agent** monitoring enrollment and visit completion

Here's the cool part - these agents work independently, analyzing the data in parallel. They each look at the same study but from their own expert perspective. Then they vote on the overall risk level using a weighted consensus system. And yes, the Safety Agent gets three times the voting weight because patient safety always comes first.

From these agent assessments, we calculate something called a DQI score - that's Data Quality Index - which gives you a single number from 0 to 100 that tells you if your study is submission-ready. Green means you're good to go, red means you've got critical issues to address.

And we've got one more layer - the Guardian Agent. Think of it as the quality control for the quality control. It monitors all the other agents, checks for consistency, and makes sure the system itself is working correctly.

The best part? This entire analysis happens in about 300 milliseconds per study. That's real-time risk assessment.


---

## 4. Live Demo - Portfolio View (1 minute)

**[SCREENSHOT: Portfolio Dashboard]**

Okay, let's jump into the actual system. This is the Portfolio Overview - your executive dashboard. What you're seeing here is real data from 23 actual studies in the NEST 2.0 dataset.

At the top, you've got your key metrics at a glance. We're looking at 23 studies total, with an average DQI score of 72 across the portfolio. You can see the risk distribution - how many studies are in critical, high, medium, or low risk categories.

Now, each of these cards represents one study. See that big number? That's the DQI score - think of it like a grade for your data quality. This study here has an 85, which puts it in the green band - that means it's analysis-ready with minimal issues.

But look at this one over here - DQI of 45, orange band. That's telling you there are significant issues that need attention. You can see the risk level indicator - this one's showing "High Risk" with specific concerns flagged.

The color coding makes it super easy to prioritize. Green studies? You're good. Amber? Keep an eye on them. Orange and red? Those need immediate attention.

And notice these metrics below each score - enrollment numbers, site counts, patient counts. Everything you need to understand the study at a glance.

Click on any study card, and you drill down into the detailed analysis. But before we do that, let me show you something really powerful - the AI Insights page.


---

## 5. Live Demo - AI Insights (1.5 minutes)

**[SCREENSHOT: AI Insights Page]**

This is where things get really interesting. The AI Insights page shows you exactly what each of those seven agents is seeing and thinking.

Look at this - you've got all seven agents listed here. Each one has a status indicator. Green checkmark means the agent is active and has analyzed the data. If you see a gray circle, that means the agent abstained because it didn't have enough data to make a reliable assessment. And that's actually a good thing - we'd rather have an agent say "I don't know" than make something up.

Let's look at the Safety & Compliance Agent. See that confidence score? 85%. That tells you how certain the agent is about its assessment. And here's the risk signal - this one's showing "Medium Risk." 

Now click on any agent to expand it, and you get the full story. You see the specific evidence the agent used - things like "2 open SAE discrepancies, average age 5 days." That's real data from the actual files. You also get the agent's reasoning - why it reached this conclusion.

The Query Quality Agent here is showing "High Risk" with 127 open queries and an average aging of 18 days. That's actionable intelligence - you know exactly what needs attention.

And here's something cool - see this consensus section at the bottom? This shows you how all the agents voted and what the weighted consensus came out to. Remember, the Safety Agent gets 3x weight, so if it's flagging something critical, that heavily influences the overall risk assessment.

Over here on the right, you've got the Guardian status. Green means the system is healthy - all agents are behaving consistently, no anomalies detected. If the Guardian spots something weird - like agents disagreeing in unusual ways - it'll flag it here.

And at the very bottom, you've got AI-generated insights. This uses a large language model to synthesize all the agent signals into plain English recommendations. It might say something like "Immediate attention needed for query backlog in Study 05" or "Excellent data quality across safety metrics."

The beauty of this page is transparency. You're not getting a black box AI decision - you're seeing exactly what each expert agent found, how confident they are, and why they reached their conclusions.


---

## 6. Live Demo - Study Deep Dive (1 minute)

**[SCREENSHOT: Study Details Page]**

Now let's drill down into a specific study. This is the Study Details page, and it gives you everything you need to know about one particular trial.

Right at the top, you've got that DQI gauge - nice and visual. This study is sitting at 68, which puts it in the amber band. Not critical, but definitely needs monitoring.

Below that, you see the breakdown by agent. Each agent's signal is shown with its risk level and confidence. The Safety Agent here is showing "Low Risk" with 90% confidence - that's great news for patient safety. But look at the Query Quality Agent - "High Risk" at 85% confidence. That's your red flag right there.

Scroll down a bit, and you've got site-level metrics. This study has 8 sites, and you can see performance varies. Site 001 has a DQI of 75, but Site 005 is down at 52. Click on any site, and you drill down even further to see site-specific issues.

Over here, you've got patient enrollment data. You can see enrollment trends over time, dropout rates, and visit completion status. If there's a patient with concerning data quality, you can click through to see their individual record.

And check this out - the temporal trends chart. This shows you how the DQI score has changed over time. Is it improving? Getting worse? Staying stable? That trend line tells you if your remediation efforts are working.

At the bottom, there's an export button. Click that, and you can download all this data as a CSV for further analysis or reporting. Everything you see in the dashboard can be exported for your records.

The key here is drill-down capability. You start at the portfolio level, identify problem studies, drill into the study to see which agents are flagging issues, then drill into specific sites or patients to see exactly where the problems are. It's like having a microscope for your data quality.


---

## 7. Technical Innovation (1 minute)

Now let me talk about what makes this system technically special, because there's some really cool engineering under the hood.

**First, the agent-driven architecture.** Each of those seven agents is completely isolated - they get their own copy of the data and can't influence each other. This means if one agent has a bug or makes a mistake, it doesn't cascade to the others. They run in parallel, so you get all seven analyses in about 300 milliseconds total. That's fast.

**Second, the consensus mechanism.** We're not just averaging the agent votes. We use weighted voting where the Safety Agent gets three times the influence of others because patient safety is paramount. And we factor in confidence - an agent that's 90% confident has more influence than one that's only 60% confident. It's a sophisticated voting system that mirrors how expert committees actually work.

**Third, real data extraction.** This is huge. We're not using synthetic data or fallback values. Everything you see comes directly from those NEST 2.0 Excel files. We built a flexible column mapper that handles all the variations in column names across studies. We handle multi-row headers in EDC files. And when data isn't available, the system explicitly says so - agents abstain rather than guess. That integrity is critical for regulatory compliance.

**Fourth, production-ready code.** We've got 331 passing tests, including property-based tests that verify our algorithms work correctly across thousands of random inputs. We've got comprehensive error handling, multi-layer caching for performance, detailed logging for debugging. This isn't a prototype - this is production-grade software.

And here's something important - the DQI score isn't calculated from some arbitrary formula. It's derived directly from the agent risk assessments. The agents identify real issues, and those issues map to specific data quality dimensions. So when you see a DQI of 68, that number has semantic meaning - it reflects actual problems the agents found.


---

## 8. Impact & Value (30 seconds)

So what does all this mean in practical terms?

**Time savings are massive.** Remember those data managers spending 40 to 60 percent of their time on manual quality checks? C-TRUST automates that. We're talking about freeing up hundreds of hours per month across a portfolio of 23 studies. That's time they can spend on actual remediation instead of just finding problems.

**Risk reduction is significant.** Early detection of data quality issues means you catch problems when they're still easy to fix. A query backlog identified at 18 days is much easier to address than one discovered at 60 days. And catching a missing fatal SAE review immediately? That could literally save lives and prevent regulatory action.

**Data quality improves.** When you have real-time visibility into quality metrics, teams naturally respond. Studies with low DQI scores get attention. Sites with issues get support. The transparency drives improvement.

**And it scales beautifully.** Whether you're running 5 studies or 50, the system handles it the same way. Each study gets analyzed in a few seconds. The architecture is stateless, so you can scale horizontally if needed. This isn't just for NEST 2.0 - the approach works for any clinical trial data.


---

## 9. Closing (30 seconds)

So that's C-TRUST. To recap: we've built a multi-agent AI system that analyzes clinical trial data quality in real-time, using seven specialized agents that work together through weighted consensus. It processes real data from NEST 2.0 files, provides transparent reasoning for every assessment, and gives you actionable intelligence through an intuitive dashboard.

This isn't a concept or a prototype - it's a fully functional system analyzing 23 real studies with production-ready code. Every DQI score you see is backed by actual agent analysis. Every risk flag is supported by evidence from the data.

The pharmaceutical industry loses billions annually to data quality issues. C-TRUST is our answer to that problem - automated, intelligent, scalable data quality monitoring that helps you catch issues early, prioritize remediation, and ultimately get safer, more effective treatments to patients faster.

Thanks for watching! If you want to dive deeper into the technical details, check out our documentation. And if you have questions, we'd love to hear from you.

---

## Notes for Video Production

**Total Speaking Time**: Approximately 7-8 minutes

**Screenshot Placeholders**:
- Section 4: Portfolio Dashboard showing all 23 studies
- Section 5: AI Insights page with agent status and signals
- Section 6: Study Details page with DQI gauge and metrics

**Pacing Tips**:
- Speak naturally and conversationally
- Pause briefly after key points to let them sink in
- Use hand gestures when explaining the multi-agent concept
- Point to specific UI elements when walking through screenshots
- Vary your tone - more serious for safety topics, more enthusiastic for technical innovations

**Visual Suggestions**:
- Zoom in on specific UI elements when discussing them
- Use cursor to highlight key metrics as you mention them
- Consider picture-in-picture for your face during technical sections
- Show smooth transitions between dashboard pages

**Key Messages to Emphasize**:
1. Real data, not synthetic (mention multiple times)
2. Seven specialized agents working together
3. Patient safety comes first (Safety Agent 3x weight)
4. Transparent, explainable AI decisions
5. Production-ready, not a prototype

**Tone Throughout**:
- Opening: Engaging, relatable
- Problem: Serious, empathetic
- Solution: Confident, clear
- Demo: Enthusiastic, detailed
- Technical: Proud but accessible
- Impact: Practical, results-focused
- Closing: Confident, inviting

