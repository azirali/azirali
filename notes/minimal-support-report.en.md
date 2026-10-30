# A support request should ask for the smallest useful report

By Olzhas Azirali / Олжас Азирали, founder of AZIRAL since 2019.

Prepared with AI assistance from the linked public support pages. The report format and examples below are design proposals, separate from the existing products' support interfaces.

![AI-created editorial cover: Olzhas Azirali in a navy blazer and white shirt, with his name and AZIRAL / BUILD NOTES on a dark blue background.](https://aziral.com/images/editorial/olzhas-azirali-build-notes-cover.jpg)

_Olzhas Azirali, founder of AZIRAL. Portrait and cover created with AI assistance._

A support request has one immediate job: help another person understand a problem well enough to choose the next useful step. A large attachment is not automatically a useful report. A short description can be more informative when it identifies the version, the action and the difference between expectation and observation.

This creates a design problem for developers. Ask too little and the first reply becomes a questionnaire. Ask for everything and people may send unrelated personal material. A better starting point is a small report whose fields each have a clear diagnostic purpose.

## Start with the public instructions

The [Bunker support page](https://bunker-friends-support.olzhadam1.chatgpt.site/support/) asks for the app version, phone model and actions before an error. [Finance Bro support](https://finance.aziral.com/support) additionally names the operating system, expected result and observed result. It also asks people to leave out passwords, verification and recovery codes, and complete unredacted bank statements.

These instructions provide a concrete starting point. The form design proposed here develops that small set of questions into an understandable request, without treating extra data as a default requirement.

## Make each field answer a question

The app version and build identify the software being discussed. Device and operating system help describe the environment. Steps identify the path through the product. Expected and observed results identify the disagreement.

Keeping those questions separate is useful. "It failed" does not say whether the app stopped, showed a message or produced an unexpected value. A prompt such as "What appeared after the last step?" invites an observation someone can describe directly.

The task belongs near the beginning too. A person trying to resume a session has a different goal from someone trying to change a preference. Naming that goal helps a maintainer understand why the reported result matters.

## Offer a compact report format

A proposed plain-text format can be enough for an initial request:

```text
Task:
App version and build:
Device model and operating system:
Steps:
Expected result:
Observed result:
Optional attachment: only the relevant part, with unrelated details removed
```

This is an editorial template, not a product API or an existing support form. It can be adapted to email, an issue tracker or a small in-app screen.

As a fictional example, imagine a person opening a saved item, changing a display preference and returning. They expected to see the saved item again, but the preferences screen remained visible. That description gives a maintainer a sequence to investigate. It does not claim that either Bunker or Finance Bro has this defect.

## Request an attachment for a reason

An attachment should answer a question left open by the initial report. A cropped screenshot might show the relevant message. An input-dependent problem might need a small synthetic example that preserves the troublesome format.

The request should name what needs to remain visible and what can be removed. Asking for a complete document when only one field is relevant makes that decision harder for the person seeking help.

A proposed follow-up could be: "Please show the message and the control immediately above it. Remove names, account details and unrelated content." That is clearer than an unexplained request for more information. Redaction and synthetic examples still require care; their purpose here is to reduce unnecessary sharing, without making a security guarantee.

## Keep observation separate from explanation

A support screen can encourage people to report what they saw before asking why they think it happened. "The previous screen remained visible" is an observation. "The database is broken" is an interpretation that may lead the conversation away from the available evidence.

Both can have a place in a discussion, but the initial report benefits from preserving that distinction. The same applies to certainty: a person may not remember one step, and the report should allow them to say so.

## Review the request as a user journey

Before shipping a support form, try completing it for a fictional problem. Can someone identify the app version, describe a short sequence and explain the result? Can they understand which attachment is optional and which information should stay out?

The useful takeaway is specific: ask for the smallest report that distinguishes the environment, action and result, then request additional material for an explained reason. This makes the next step in support easier to understand while keeping the initial burden limited.

Product context: Finance Bro is developed on an open-source Flutter foundation, as disclosed in its [product note](https://aziral.com/en/build-notes/finance-bro). Public support materials were checked on 30 October 2026; their instructions can change with the product.
