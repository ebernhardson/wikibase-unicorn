# Unicorn Graph Query Language for Wikibase

Wikibase Unicorn is a minimal implementation of the unicorn graph query language (pdf). It provides graph search over
wikibase + cirrussearch enabled wikis by performing recursive queries against the elasticsearch instances containing the
CirrusSearch indices.

## Example

Owners of hospitals. More exactly, owners of instances of hospitals and owners of instances of subclasses of hospitals.

    (extract P127=
             (or P31=Q16917
                 (apply P31= P279=Q16917)))

## Live Instance

https://wikibase-unicorn.toolforge.org/

## Implemented Operators

|  Operator  |         Example S-expression         |                 Description                 |
|:-----------|:-------------------------------------|:--------------------------------------------|
|            | P31=Q16917                           | Instances of hospitals                      |
| term       | (term P31=Q16917)                    | Instances of hospitals                      |
| and        | (and P31=Q16917 P31=Q1774898)        | Instances of hospitals and clinics          |
| or         | (or P31=Q16917 P31=Q1774898)         | Instances of hospitals or clinics           |
| difference | (difference P31=Q16917 P31=Q1774898) | Instances of hospitals that are not clinics |
| apply      | (apply P31= P279=Q16917)             | Instances of subclasses of hospital         |
| extract    | (extract P127= P31=Q16917)           | Owners of instances of hospitals            |

Instance-of is P31, subclass-of is P279, owned-by is P127. Hospital is Q16917, clinic is Q1774898.

## How does it work?

For wikibase enabled wikis CirrusSearch maintains a field per Q-item called `statement_keywords` which contains a
filtered set of the graph edges each in the form `P1=Q1`. The provided unicorn query is transformed into equivalent
elasticsearch queries and edges in the graph are followed by performing sequential elasticsearch queries. Because there
are execution boundaries between stages, and elasticsearch can only accept 1024 conditions in a single search request,
results from Wikibase Unicorn can only provide a completeness guarantee when the truncated metric reported after all
search results is zero.  Results are truncated based on the number of sitelinks, the pages with the lowest number of
sitelinks are removed. Per the linked paper truncation is typical not an issue for user-facing (small N relevant
results) queries as long as inner-query sorting is doing a good job. Inner query sorting in this implementation is
likely sub-par (also by `sitelink_count`).
