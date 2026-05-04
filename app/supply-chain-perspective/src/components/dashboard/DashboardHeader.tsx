import { Button, Flex, FlexItem, Spinner, Title } from '@patternfly/react-core';
import { OutlinedMoonIcon, SunIcon } from '@patternfly/react-icons';
import { useTranslation } from 'react-i18next';

export interface DashboardHeaderProps {
  isLightTheme: boolean;
  loading: boolean;
  onToggleTheme: () => void;
}

export function DashboardHeader({ isLightTheme, loading, onToggleTheme }: DashboardHeaderProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  return (
    <div className="supply-chain-perspective__dashboard-header">
      <Flex
        alignItems={{ default: 'alignItemsCenter' }}
        justifyContent={{ default: 'justifyContentSpaceBetween' }}
        flexWrap={{ default: 'nowrap' }}
      >
        <FlexItem>
          <Title headingLevel="h1" size="2xl">
            {t('Supply Chain Command Center')}
          </Title>
        </FlexItem>
        <FlexItem>
          <Flex
            alignItems={{ default: 'alignItemsCenter' }}
            spaceItems={{ default: 'spaceItemsMd' }}
          >
            {loading ? (
              <FlexItem>
                <Spinner size="md" aria-label={t('Refreshing data')} />
              </FlexItem>
            ) : null}
            <FlexItem>
              <Button
                variant="plain"
                aria-label={t('Toggle color theme')}
                icon={isLightTheme ? <OutlinedMoonIcon /> : <SunIcon />}
                onClick={onToggleTheme}
              />
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>
    </div>
  );
}
