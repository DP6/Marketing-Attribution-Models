# Contributing guide

Thank you for your help making penguin-datalayer-collect better! Every contribution is appreciated. There are many areas where you can contribute.

::: tip Submit issue first
If you plan to implement a new feature or some other change please create an issue first, to make sure that your work is not lost.
:::

[[toc]]

## Documentation

pinguin-datalayer-collect has a lot of features and maintaining documentation takes time. If anything is unclear, or could be explained better, we appreciate the time you spend correcting or clarifying it.

There is a link in the bottom of each website page to quickly edit it.

## Issues

Before submitting the issue:

- Search the existing issues
- Review [Frequently Asked Questions](./docs/faq.md).
- Provide all the relevant information, reducing both your schema and data to the smallest possible size when they still have the issue.

We value simplicity - simplifying the example that shows the issue makes it more valuable for other users. This process helps us reduce situations where an error is occurring due to incorrect usage rather than a bug.

### Bug reports

Please make sure to include the following information in the issue:

1. What version of are you using?
2. Does the issue happen if you use the latest version?
3. Schema and the data you are validating (please make it as small as possible to reproduce the issue).
5. Your code sample (please use `schema` and `data` as variables).
6. Validation result, data AFTER validation, error messages.
7. What results did you expect?

[Create bug report](https://github.com/dp6/penguin-datalayer-collect/issues/new?template=bug_report.md).

### Security vulnerabilities

To report a security vulnerability, please use the e-mail koopas@dp6.com.br.

Please do NOT report security vulnerabilities via GitHub issues.

### <a name="changes"></a>Change proposals

[Create a proposal](https://github.com/dp6/penguin-datalayer-collect/issues/new?template=feature_request.md) for a new feature, option or some other improvement.

Please include this information:

1. The version you are using.
2. The problem you want to solve.
3. Your solution to the problem.
4. Would you like to implement it?

If you’re requesting a change, it would be helpful to include this as well:

1. What you did.
2. What happened.
3. What you would like to happen.

Please include as much details as possible - the more information, the better.

### <a name="installation"></a>Installation and dependency issues

[Create an issue](https://github.com/dp6/penguin-datalayer-collect/issues/new?template=bug_report.md) to report problems that happen during penguin-datalayer-collect installation or when penguin-datalayer-collect is missing some dependency.

Before submitting the issue, please try the following:

- use the latest stable Node.js and `npm`
- try using `yarn` instead of `npm` - the issue can be related to https://github.com/npm/npm/issues/19877
- remove `node_modules` and `package-lock.json` and run `npm install` again

If nothing helps, please submit:

1. The version you are using
2. Operating system and Node.js version
3. Package manager and its version
4. Link to (or contents of) package.json and package-lock.json
5. Error messages
6. The output of `npm ls`

## Code

Thanks a lot for considering contributing to penguin-datalayer-collect! Our users have created many great features, and we look forward to your contributions.

#### Development

Running tests:

```bash
npm install
npm test
```

#### Pull requests

We want to iterate on the code efficiently. To speed up the process, please follow these steps:

1. Submit an [issue with the bug](https://github.com/dp6/penguin-datalayer-collect/issues/new) or with the proposed change (unless the contribution is to fix the documentation typos and mistakes).
2. Describe the proposed api and implementation plan (unless the issue is a relatively simple bug and fixing it doesn't change any api).
3. Once agreed, please write as little code as possible to achieve the desired result. We are passionate about keeping our library size optimized.
4. Please add the tests both for the added feature and, if you are submitting an option, for the existing behaviour when this option is turned off or not passed.
5. Please avoid unnecessary changes, refactoring or changing coding styles as part of your change (unless the change was proposed as refactoring).
6. Follow the coding conventions even if they are not validated.
7. Please run the tests before committing your code.
8. If tests fail in CI build after you make a PR please investigate and fix the issue.

#### Contributions license

When contributing the code you confirm that:

1. Your contribution is created by you.
2. You have the right to submit it under the Apache-2.0 license.
3. You understand and agree that your contribution is public, will be stored indefinitely, can be redistributed as the part of penguin-datalayer-collect or another related package under Apache-2.0 license, modified or completely removed from penguin-datalayer-collect.
4. You grant irrevocable Apache-2.0 license to use your contribution as part of penguin-datalayer-collect or any other package.
5. You waive all rights to your contribution.
6. Unless you request otherwise, you can be mentioned as the author of the contribution in the penguin-datalayer-collect documentation and change log.

## Attribution

This Code of Conduct is adapted from the [Ajv][homepage],
available at https://ajv.js.org/code_of_conduct/

[homepage]: https://ajv.js.org/