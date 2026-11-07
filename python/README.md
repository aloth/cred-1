# cred1

Python access to [CRED-1](https://github.com/aloth/cred-1), an open dataset of credibility ratings for 2,600+ news and website domains. The dataset ships inside the package, so lookups work offline.

```bash
pip install cred1
pip install "cred1[pandas]"   # for to_dataframe()
```

```python
import cred1

cred1.check("https://www.infowars.com/some/article")
# {'domain': 'infowars.com', 'score': 0.14, 'category': 'fake', 'level': 'low', 'sources': 2, ...}

cred1.check("example.com")        # None: not listed
cred1.check_many(["a.com", "b.com"])
cred1.search("news")              # matching domains, least credible first
cred1.stats()                     # total and per-category counts
df = cred1.to_dataframe()         # whole dataset as a pandas DataFrame
```

`score` runs from 0.0 to 1.0, lower is less credible; `level` is `low` (up to 0.2), `mixed` (up to 0.5) or `ok`. A domain that is not listed is not rated, which is not the same as credible.

The package version is the dataset release date (CalVer), the same as the npm package [`@aloth/cred1`](https://www.npmjs.com/package/@aloth/cred1), which adds a command-line tool and an MCP server.

## Citation

If you use CRED-1 in research, please cite the dataset: [doi:10.5281/zenodo.18769459](https://doi.org/10.5281/zenodo.18769459). GitHub's "Cite this repository" button on [aloth/cred-1](https://github.com/aloth/cred-1) gives the reference in APA and BibTeX.

## License

Code: MIT. Dataset: CC BY 4.0.
