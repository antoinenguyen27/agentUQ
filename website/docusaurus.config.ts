import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';

const previewUrl = process.env.VERCEL_URL
  ? `https://${process.env.VERCEL_URL}`
  : undefined;
const url = process.env.DOCS_SITE_URL ?? previewUrl ?? 'https://agentuq.vercel.app';
const baseUrl = process.env.DOCS_BASE_URL ?? '/';

const config: Config = {
  title: 'AgentUQ',
  tagline: 'Localized runtime reliability gates for LLM agents.',
  favicon: 'img/agentuq-mark.svg',
  url,
  baseUrl,
  organizationName: 'antoinenguyen27',
  projectName: 'agentUQ',
  trailingSlash: false,
  onBrokenLinks: 'throw',
  onDuplicateRoutes: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
    },
  },
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          include: ['**/*.{md,mdx}'],
          exclude: ['**/_*.{md,mdx}'],
          lastVersion: 'current',
          versions: {
            current: {
              label: '0.1.0',
            },
          },
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'AgentUQ',
      logo: {
        alt: 'AgentUQ',
        src: 'img/agentuq-mark.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/get-started/quickstart',
          label: 'Quickstart',
          position: 'left',
        },
        {
          to: '/reference/api',
          label: 'API',
          position: 'left',
        },
        {
          to: '/',
          label: 'v0.1.0',
          position: 'right',
        },
        {
          href: 'https://github.com/antoinenguyen27/agentUQ',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    docs: {
      sidebar: {
        autoCollapseCategories: true,
        hideable: true,
      },
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Get Started',
          items: [
            {label: 'Overview', to: '/'},
            {label: 'Install', to: '/get-started/install'},
            {label: 'Quickstart', to: '/get-started/quickstart'},
          ],
        },
        {
          title: 'Core Docs',
          items: [
            {label: 'Concepts', to: '/concepts'},
            {label: 'Reference', to: '/reference/api'},
            {label: 'Quickstarts', to: '/quickstarts'},
          ],
        },
        {
          title: 'Project',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/antoinenguyen27/agentUQ',
            },
            {
              label: 'MIT License',
              href: 'https://github.com/antoinenguyen27/agentUQ/blob/main/LICENSE.txt',
            },
            {
              label: 'Maintainers',
              to: '/maintainers',
            },
            {
              label: 'Integration source review',
              to: '/maintainers/integration-source-review',
            },
          ],
        },
      ],
      copyright: `Copyright ${new Date().getFullYear()} AgentUQ OSS Contributors. Released under the MIT License.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python'],
    },
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: true,
    },
  },
};

export default config;
