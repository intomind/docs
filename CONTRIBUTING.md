# Contributing

Issues, questions, and pull requests are welcome.

## Before your first pull request

Sign the contributor license agreement. It is short, it is in `CLA.md`,
and it is signed once rather than per contribution. Comment on your pull
request with:

```
I have read CLA.md and I agree to it.
```

from the account that owns the contribution. A maintainer records the
agreement against your account and later pull requests need nothing
further.

You keep the copyright in your work. The agreement gives IntoMind the
right to use your contribution under both the Affero license and the
commercial license, which is what makes it possible to offer either one.
Without it a contribution could only ever go out under one of them, and
the project would have to refuse the contribution or drop the commercial
license.

If you are contributing for an employer, get whoever owns your work to
agree as well, and say so on the pull request.

## What makes a change easy to accept

- One change per pull request, with the reason in the message rather than
  in a comment on the diff.
- The change made to the Markdown in `pages/`. A maintainer rebuilds the
  site and runs the checks, which read files kept on maintainers'
  machines.
- The house style: American English, plain sentences, no abbreviation a
  reader has to look up.
- A claim a reader can check: a number from a measurement, a name that
  exists in the code.

## The protocol pages

The protocol pages are assembled from the protocol's own documents, so
that a released version and its documentation cannot disagree. Those
documents are not in this repository. To change a protocol page, open an
issue and say what is wrong.

## What gets refused

- Text you did not write, or text whose license is not compatible.
- A framework, a build toolchain, or a dependency. The site is plain
  Markdown turned into plain HTML by one script.
- A claim nobody measured.

## Security

Report anything security sensitive to contact@intomind.com rather than in
a public issue.
