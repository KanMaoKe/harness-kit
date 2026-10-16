"""Optional project governance modules and their generated scaffolds."""
MODULES = ('bugs', 'design', 'adr', 'sessions', 'debt', 'features')


def parse_selection(value):
    if not value:
        return []
    names = [item.strip().lower() for item in value.split(',') if item.strip()]
    unknown = sorted(set(names) - set(MODULES))
    if unknown:
        raise ValueError('未知模块：%s（可选：%s）' % (', '.join(unknown), ', '.join(MODULES)))
    if len(names) != len(set(names)):
        raise ValueError('--modules 中有重复模块')
    return names


def configuration(meta):
    """Return normalized module settings stored in HARNESS.json."""
    raw = meta.get('modules', {})
    if not isinstance(raw, dict):
        raise ValueError('HARNESS.json 的 modules 必须是对象')
    unknown = sorted(set(raw) - set(MODULES))
    if unknown:
        raise ValueError('HARNESS.json 包含未知模块：%s' % ', '.join(unknown))
    result = {}
    for name, value in raw.items():
        if isinstance(value, bool):
            enabled = value
            options = {}
        elif isinstance(value, dict) and type(value.get('enabled')) is bool:
            enabled = value['enabled']
            options = value
        else:
            raise ValueError('HARNESS.json 的 modules.%s 必须包含布尔值 enabled' % name)
        config = {'enabled': enabled}
        if name == 'debt':
            storage = options.get('storage', 'list')
            if storage not in ('list', 'entries'):
                raise ValueError('HARNESS.json 的 modules.debt.storage 必须是 list 或 entries')
            config['storage'] = storage
        result[name] = config
    return result


def update_configuration(current, enable=(), disable=(), debt_storage=None):
    result = {name: dict(options) for name, options in current.items()}
    for name in enable:
        result.setdefault(name, {'enabled': True})
        result[name]['enabled'] = True
        if name == 'debt':
            result[name].setdefault('storage', 'list')
    for name in disable:
        if name in result:
            result[name]['enabled'] = False
    if debt_storage:
        if 'debt' not in enable and not result.get('debt', {}).get('enabled'):
            raise ValueError('--debt-storage 需要启用 debt 模块')
        result.setdefault('debt', {'enabled': True})
        result['debt']['enabled'] = True
        result['debt']['storage'] = debt_storage
    return result


def active(config):
    return [name for name in MODULES if config.get(name, {}).get('enabled')]


def file_specs(config):
    """Return (project-relative path, template-relative path) pairs."""
    specs = []
    enabled = set(active(config))
    mappings = {
        'bugs': [('bugs/README.md', 'bugs/README.md.tpl'),
                 ('bugs/BUG_TEMPLATE.md', 'bugs/BUG_TEMPLATE.md.tpl')],
        'design': [('design/README.md', 'design/README.md.tpl'),
                   ('design/DESIGN_TEMPLATE.md', 'design/DESIGN_TEMPLATE.md.tpl')],
        'adr': [('adrs/README.md', 'adr/README.md.tpl'),
                ('adrs/ADR_TEMPLATE.md', 'adr/ADR_TEMPLATE.md.tpl')],
        'sessions': [('sessions/README.md', 'sessions/README.md.tpl'),
                     ('sessions/SESSION_TEMPLATE.md', 'sessions/SESSION_TEMPLATE.md.tpl')],
        'features': [('features/README.md', 'features/README.md.tpl'),
                     ('features/FEATURE_REGISTRY.md', 'features/FEATURE_REGISTRY.md.tpl'),
                     ('features/ACTIVE_WORK.md', 'features/ACTIVE_WORK.md.tpl')],
    }
    for name in ('bugs', 'design', 'adr', 'sessions', 'features'):
        if name in enabled:
            specs.extend(mappings[name])
    if 'debt' in enabled:
        if config['debt'].get('storage', 'list') == 'entries':
            specs.extend([('debt/README.md', 'debt/README.md.tpl'),
                          ('debt/DEBT_TEMPLATE.md', 'debt/DEBT_TEMPLATE.md.tpl')])
        else:
            specs.append(('TECH_DEBT.md', 'debt/TECH_DEBT.md.tpl'))

    if enabled.intersection(('bugs', 'design', 'adr', 'sessions')) or (
            'debt' in enabled and config['debt'].get('storage') == 'entries'):
        specs.append(('RECORDS.md', 'RECORDS.md.tpl'))
    return specs
