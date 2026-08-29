# Contributing

Issues and small, security-conscious pull requests are welcome.

1. Discuss verdict or schema changes in an issue first.
2. Fork the repository and branch from `main`.
3. Keep runtime dependencies at zero unless the security/portability tradeoff is
   documented and accepted.
4. Add a regression fixture for every fail-closed behavior change.
5. Run:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -v
   PYTHONPATH=src python3 scripts/run_demo.py
   python3 -m compileall -q src tests scripts
   actionlint
   python3 scripts/validate_release.py
   ```

6. Explain whether the change affects the RFC, threat model, manifest, receipt,
   permissions, or compatibility.

Never paste real private repository names, tokens, check URLs or incident data
into fixtures. Security reports follow [SECURITY.md](SECURITY.md), not issues.

By contributing, you agree that your contribution is licensed under Apache-2.0.
