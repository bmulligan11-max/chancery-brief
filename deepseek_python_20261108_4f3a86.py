"""Chancery Brief - daily build script.
Search via Tavily, writing via DeepSeek.
"""
import datetime
import html
import json
import os
import pathlib
import re
import sys
import requests

ROOT = pathlib.Path(__file__).parent
DEEPSEEK_BASE = "https://api.deepseek.com"
TAVILY_URL = "https://api.tavily.com/search"
POST = "Beijing"

SOURCES = [...]

SYSTEM = (...)

PROMPT = """..."""


def search_tavily(query, days=3):
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY not set")
    r = requests.post(
        TAVILY_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "query": query,
            "search_depth": "basic",
            "max_results": 6,
            "days": days,
            "include_answer": False,
            "include_raw_content": False,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def write_deepseek(prompt):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    r = requests.post(
        f"{DEEPSEEK_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 8000,
        },
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def fetch():
    today = datetime.date.today().strftime("%A %d %B %Y")
    queries = [
        China Strategic Intelligence & Policy Monitor

Produce a comprehensive, analytically rigorous monitoring brief focused on China's foreign policy, domestic political decision-making, strategic objectives, and international activities.

Prioritize developments from the last 72 hours. Where relevant, extend the research window to identify important developments, policy trajectories, and background context that explain current events.

1. Core Monitoring Priorities

Monitor and investigate the following areas:

Chinese leadership and the MFA: Xi Jinping, Politburo, Politburo Standing Committee, Central Foreign Affairs Commission, Ministry of Foreign Affairs (MFA), Wang Yi, and other senior political and diplomatic figures. Track leadership activity, statements, meetings, personnel changes, policy signals, and institutional decisions.

US-China relations: Trade negotiations, tariffs, export controls, sanctions, technology restrictions, investment screening, strategic competition, diplomatic engagement, and economic coercion.

Technology and AI policy: China's AI ambitions, semiconductor strategy, technology self-sufficiency, industrial policy, data governance, AI regulation, advanced computing, and competition with the United States.

Chinese commercial space and launches: Commercial space companies, launch activity, satellite constellations, government-private sector relationships, space infrastructure, and the strategic implications of China's expanding space capabilities.

The Chinese economy: Economic performance, industrial policy, domestic consumption, trade, investment, financial stability, property markets, employment, supply chains, and central government economic decisions.

Taiwan and regional security: Cross-Strait relations, PLA activity, military modernization, deterrence, regional alliances, South China Sea, East China Sea, and China's relations with neighboring countries.

APEC and international diplomacy: China's engagement with APEC, multilateral institutions, the Global South, Europe, ASEAN, and other diplomatic forums. Track bilateral meetings, diplomatic initiatives, and efforts to shape international institutions and norms.

2. Chinese Foreign Policy Objectives and Strategic Intent

Go beyond reporting individual events. Investigate what China's leadership is trying to achieve.

For significant developments, assess:

What are China's underlying foreign policy objectives?

What strategic interests or perceived threats are driving its actions?

How do developments fit into Xi Jinping's broader foreign policy vision?

What does Beijing want to change, preserve, prevent, or achieve in the international system?

How is China attempting to reshape its relationships with the United States, Europe, Russia, developing countries, and regional neighbors?

What are the implications for China's long-term strategic competition with the United States?

Are Chinese actions primarily defensive, opportunistic, coercive, or designed to establish new strategic advantages?

Distinguish between China's publicly stated objectives and its likely strategic intentions. Clearly identify where assessments are inferential rather than explicitly documented.

3. Internal Chinese Politics and Policy Decision-Making

Give particular attention to political decisions, policy debates, and strategic discussions occurring within China itself.

Research and identify:

Decisions and policy signals emerging from the CCP leadership, Politburo, Politburo Standing Committee, Central Committee, State Council, and relevant party commissions.

Internal political priorities influencing foreign policy and economic decision-making.

Policy debates among Chinese officials, academics, policy advisers, economists, military analysts, think tanks, and influential intellectuals.

Differences in institutional perspectives between the CCP, MFA, PLA, economic ministries, state-owned enterprises, technology regulators, and provincial authorities.

Debates over economic reform, nationalism, US-China relations, Taiwan, technological self-reliance, globalization, and China's international position.

Changes in official language, policy terminology, ideological messaging, and leadership rhetoric that may signal shifts in priorities.

Personnel appointments, dismissals, investigations, disciplinary actions, and changes in institutional authority that could affect policy direction.

Evidence of policy disagreements, competing priorities, implementation problems, or tensions between political objectives and economic realities.

Do not assume that China has a single, perfectly unified policy position. Where evidence permits, examine competing institutional interests, different policy perspectives, and disagreements within China's political and intellectual establishment.

Do not invent internal debates or claim access to confidential deliberations. Use publicly available evidence, Chinese-language sources, official documents, academic publications, and credible reporting to reconstruct the policy discussion.

4. Chinese-Language Research: Essential

Do not rely exclusively on English-language reporting.

Actively research Chinese-language sources to identify developments, political debates, and perspectives that may be overlooked by international media.

Prioritize:

CCP and government publications and official statements.

Xinhua, People's Daily, Qiushi, and other authoritative party-state media.

Ministry of Foreign Affairs and State Council publications.

Chinese academic journals and university research.

Chinese foreign policy and international relations scholars.

Chinese economic and technology research institutions.

PLA-related publications and military-affiliated research.

Chinese think tanks and policy research organizations.

Chinese-language commentary, interviews, and debates among policy specialists.

Relevant provincial and local government announcements.

Where useful, compare Chinese-language coverage with English-language reporting to identify differences in emphasis, framing, omissions, and political messaging.

Translate and explain important Chinese policy terminology rather than relying on literal translations.

5. Analytical Assessment

For each major development, address:

What happened? Establish the facts and timeline.

What did Beijing say? Identify official positions and statements.

What is happening inside China? Identify relevant political decisions, policy debates, institutional interests, and domestic pressures.

Why does it matter? Explain the strategic and political significance.

What is China trying to achieve? Assess the underlying objectives and intended outcomes.

What are the implications? Evaluate consequences for the United States, Taiwan, regional security, international trade, technology, and global diplomacy.

What happens next? Identify indicators, upcoming decisions, events, and potential policy changes to watch.

Separate verified facts, official claims, informed analysis, and speculation.

6. Research and Source Standards

Prioritize developments published within the previous 72 hours.

Include older material only when necessary to explain an important policy development or strategic trajectory.

Use primary sources wherever possible, including Chinese government documents, leadership speeches, policy announcements, regulatory notices, and original Chinese-language publications.

Cross-reference important developments with multiple credible sources.

Include direct links to original sources.

Provide publication dates and distinguish the date of publication from the date of the event.

Identify the source's institutional affiliation and potential political perspective where relevant.

Highlight important Chinese-language sources even when English-language coverage is limited.

Do not present official Chinese statements as independent verification of events.

Avoid repetitive reporting and low-value commentary.

7. Final Brief Structure

Organize the monitoring brief as follows:

A. Executive Intelligence Summary
The 5–10 most consequential developments, with emphasis on what they reveal about China's strategic direction.

B. Leadership and Internal Political Developments
Xi Jinping, CCP leadership, MFA, personnel changes, policy decisions, institutional dynamics, and internal debates.

C. Foreign Policy and Strategic Objectives
China's diplomatic priorities, international positioning, relations with major powers, and longer-term strategic ambitions.

D. US-China Relations
Trade, export controls, sanctions, technology, economic competition, and diplomacy.

E. Taiwan and Regional Security
Cross-Strait developments, PLA activity, regional diplomacy, and security implications.

F. Technology, AI, and Commercial Space
AI, semiconductors, industrial strategy, commercial space companies, and launch activity.

G. Economy and Domestic Policy
Macroeconomic developments, industrial policy, economic reform, domestic political considerations, and implementation challenges.

H. APEC and Wider Diplomacy
Multilateral engagement, bilateral diplomacy, Global South outreach, and international institutional strategy.

I. Inside China: Policy Debates and Competing Perspectives
The most important publicly observable debates among Chinese officials, academics, policy advisers, think tanks, and institutional actors. Identify emerging arguments, disagreements, and changes in policy thinking.

J. Strategic Outlook and Indicators to Watch
Identify the most important emerging trends, potential policy shifts, upcoming decisions, and indicators that could signal a change in China's strategic direction.

8. Overall Analytical Objective

The purpose of this monitor is not simply to summarize news about China.

It is to develop a deeper understanding of how China's political system makes decisions, how domestic political and economic considerations shape its foreign policy, what strategic objectives guide its international behavior, and how competing perspectives within China influence policy outcomes.

Prioritize insight over volume, primary evidence over commentary, Chinese-language research over reliance on Western interpretations, and strategic analysis over routine news summaries.

The central question should always be:

What is happening inside China, what is the leadership trying to achieve externally, why is it pursuing these objectives, and what do the developments reveal about China's evolving strategic direction?
    ]
    results = []
    for q in queries:
        try:
            results.extend(search_tavily(q, days=3))
        except Exception as e:
            print(f"Search failed for {q}: {e}")

    # dedupe by URL
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    context_parts = []
    for r in unique[:25]:
        context_parts.append(
            f"Title: {r.get('title','')}\n"
            f"URL: {r.get('url','')}\n"
            f"Date: {r.get('published_date','')}\n"
            f"Content: {r.get('content','')[:900]}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = PROMPT.replace("TODAY", today)
    prompt += f"\n\nHere are the search results you must use. Only use facts from these:\n\n{context}"

    raw = write_deepseek(prompt)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("No JSON found in response: " + raw[:300])
    data = json.loads(m.group(0))
    data["date"] = datetime.date.today().isoformat()
    data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return data
