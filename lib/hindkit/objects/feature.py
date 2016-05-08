#!/usr/bin/env AFDKOPython
# encoding: UTF-8
from __future__ import division, absolute_import, print_function, unicode_literals

import os, collections
import WriteFeaturesKernFDK, WriteFeaturesMarkFDK
import hindkit as kit

def glyph_filter_marks(family, glyph):
    has_mark_anchor = False
    for anchor in glyph.anchors:
        if anchor.name:
            if anchor.name.startswith('_'):
                has_mark_anchor = True
                break
    return has_mark_anchor

def sort_names(names, order=None):
    sorted_names = (
        [i for i in order if i in names] +
        [i for i in names if i not in order]
    )
    return sorted_names

class Feature(kit.BaseFile):

    def __init__(self, project, name, optional_filenames=None):
        super(Feature, self).__init__(name, project=project)
        self.optional_filenames = kit.fallback(optional_filenames, [])
        self.file_format = 'FEA'
        self.abstract_directory = kit.Project.directories['features']

    @staticmethod
    def compose_glyph_class_def_lines(class_name, glyph_names):
        if glyph_names:
            glyph_class_def_lines = (
                ['@{} = ['.format(class_name)] +
                ['  {}'.format(glyph_name) for glyph_name in glyph_names] +
                ['];', '']
            )
        else:
            glyph_class_def_lines = ['# @{} = [];'.format(class_name), '']
        return glyph_class_def_lines

    def generate(self, style=None):

        if self.name == 'classes':
            self.generate_classes()
        elif self.name == 'tables':
            self.generate_tables()
        elif self.name == 'languagesystems':
            self.generate_languagesystems()
        elif self.name == 'GPOS':
            self.generate_gpos(style)
        elif self.name == 'WeightClass':
            self.generate_weight_class(style)
        elif self.name == 'features':
            self.generate_references(style)

    def generate_classes(self):

        lines = []

        if self.project.options['prepare_mark_positioning']:

            glyph_classes = []
            glyph_classes.extend([(WriteFeaturesMarkFDK.kCombMarksClassName, glyph_filter_marks)])

            if self.project.options['match_mI_variants']:
                glyph_classes.extend([
                    ('MATRA_I_ALTS', kit.misc.glyph_filter_matra_i_alts),
                    ('BASES_ALIVE', kit.misc.glyph_filter_bases_alive),
                    ('BASES_DEAD', kit.misc.glyph_filter_bases_dead),
                    # ('BASES_FOR_WIDE_MATRA_II', kit.misc.glyph_filter_bases_for_wide_matra_ii),
                ])

            style_0 = self.project.products[0].style.open()

            glyph_order = self.project.glyph_data.glyph_order
            for class_name, filter_function in glyph_classes:
                glyph_names = [
                    glyph.name for glyph in filter(
                        lambda glyph: filter_function(self.project.family, glyph),
                        style_0,
                    )
                ]
                glyph_names = sort_names(glyph_names, glyph_order)
                style_0.groups.update({class_name: glyph_names})
                lines.extend(
                    self.compose_glyph_class_def_lines(class_name, glyph_names)
                )
            style_0.save()

            for style in (product.style for product in self.project.products[1:]):
                font = style.open()
                font.groups.update(style_0.groups)
                font.save()

        if lines:
            with open(self.path, 'w') as f:
                f.writelines(i + '\n' for i in lines)

    def generate_tables(self):

        info = self.project.family.info
        client = kit.Client(self.project.family)

        lines = []
        tables = collections.OrderedDict([
            ('hhea', []),
            ('OS/2', []),
            ('GDEF', []),
            ('name', []),
        ])

        tables['OS/2'].extend([
            'include (weightclass.fea);',
            'fsType {};'.format(client.table_OS_2['fsType']),
            'Vendor "{}";'.format(client.table_OS_2['Vendor']),
        ])

        set_vertical_metrics = False
        for field in (
            info.openTypeHheaAscender,
            info.openTypeHheaDescender,
            info.openTypeHheaLineGap,
            info.openTypeOS2TypoAscender,
            info.openTypeOS2TypoDescender,
            info.openTypeOS2TypoLineGap,
            info.openTypeOS2WinAscent,
            info.openTypeOS2WinDescent,
        ):
            if field is not None:
                set_vertical_metrics = True
                break

        if set_vertical_metrics:

            if info.unitsPerEm is None:
                raise SystemExit("`family.info.unitsPerEm` is unavailable.")

            if info.openTypeHheaAscender is None:
                info.openTypeHheaAscender = 800
            if info.openTypeHheaDescender is None:
                info.openTypeHheaDescender = -200
            if info.openTypeHheaLineGap is None:
                info.openTypeHheaLineGap = 0

            if client.vertical_metrics_strategy == 'Google Fonts':
                if info.openTypeOS2TypoAscender is None:
                    info.openTypeOS2TypoAscender = info.openTypeHheaAscender
                if info.openTypeOS2TypoDescender is None:
                    info.openTypeOS2TypoDescender = info.openTypeHheaDescender
                if info.openTypeOS2TypoLineGap is None:
                    info.openTypeOS2TypoLineGap = info.openTypeHheaLineGap
            elif client.vertical_metrics_strategy == 'ITF':
                extra_height = info.openTypeHheaAscender - info.openTypeHheaDescender - info.unitsPerEm
                if info.openTypeOS2TypoAscender is None:
                    info.openTypeOS2TypoAscender = info.openTypeHheaAscender - int(round(extra_height / 2))
                if info.openTypeOS2TypoDescender is None:
                    info.openTypeOS2TypoDescender = info.openTypeOS2TypoAscender - info.unitsPerEm
                if info.openTypeOS2TypoLineGap is None:
                    info.openTypeOS2TypoLineGap = info.openTypeHheaLineGap + extra_height

            if info.openTypeOS2WinAscent is None:
                info.openTypeOS2WinAscent = info.openTypeHheaAscender
            if info.openTypeOS2WinDescent is None:
                info.openTypeOS2WinDescent = abs(info.openTypeHheaDescender)

            tables['hhea'].extend([
                'Ascender {};'.format(info.openTypeHheaAscender),
                'Descender {};'.format(info.openTypeHheaDescender),
                'LineGap {};'.format(info.openTypeHheaLineGap),
            ])
            tables['OS/2'].extend([
                'TypoAscender {};'.format(info.openTypeOS2TypoAscender),
                'TypoDescender {};'.format(info.openTypeOS2TypoDescender),
                'TypoLineGap {};'.format(info.openTypeOS2TypoLineGap),
                'winAscent {};'.format(info.openTypeOS2WinAscent),
                'winDescent {};'.format(info.openTypeOS2WinDescent),
            ])

        # tables['OS/2'].extend(self.project.generate_UnicodeRange)
        # tables['OS/2'].extend(self.project.generate_CodePageRange)

        if self.project.options['override_GDEF']:
            GDEF_records = {
                'bases': '',
                'ligatures': '',
                'marks': '',
                'components': '',
            }
            if self.project.options['prepare_mark_positioning'] or os.path.exists(os.path.join(self.directory, 'classes.fea')):
                GDEF_records['marks'] = '@{}'.format(WriteFeaturesMarkFDK.kCombMarksClassName)
            if os.path.exists(os.path.join(self.directory, 'classes_suffixing.fea')):
                GDEF_records['marks'] = '@{}'.format('COMBINING_MARKS_GDEF')
            tables['GDEF'].extend([
                'GlyphClassDef {bases}, {ligatures}, {marks}, {components};'.format(**GDEF_records)
            ])

        tables['name'].extend(
            'nameid {} "{}";'.format(
                name_id,
                content.encode('unicode_escape').replace('\\x', '\\00').replace('\\u', '\\')
            )
            for name_id, content in client.table_name.items()
            if content
        )

        for name, entries in tables.items():
            if entries:
                lines.append('table {} {{'.format(name))
                lines.extend('  ' + i for i in entries)
                lines.append('}} {};'.format(name))

        if lines:
            with open(self.path, 'w') as f:
                f.writelines(i + '\n' for i in lines)

    def generate_languagesystems(self):

        lines = ['languagesystem DFLT dflt;']
        for tag in self.project.family.script.tags:
            lines.append('languagesystem {} dflt;'.format(tag))

        if lines:
            with open(self.path, 'w') as f:
                f.writelines(i + '\n' for i in lines)

    def generate_gpos(self, style):

        directory = style.directory

        if self.project.options['prepare_kerning']:

            WriteFeaturesKernFDK.KernDataClass(
                font = style.open(),
                folderPath = directory,
            )

            try:
                self.project.postprocess_kerning
            except AttributeError:
                pass
            else:
                kern_path = os.path.join(
                    directory,
                    WriteFeaturesKernFDK.kKernFeatureFileName,
                )
                if os.path.exists(kern_path):
                    with open(kern_path) as f:
                        content = f.read()
                    with open(kern_path, 'w') as f:
                        f.write(self.project.postprocess_kerning(content))

        if self.project.options['prepare_mark_positioning']:
            WriteFeaturesMarkFDK.MarkDataClass(
                font = style.open(),
                folderPath = directory,
                trimCasingTags = False,
                genMkmkFeature = self.project.options['prepare_mark_to_mark_positioning'],
                writeClassesFile = True,
                indianScriptsFormat = self.project.family.script.is_indic,
            )
            if self.project.options['match_mI_variants']:
                adjustment_extremes = self.get_adjustment_extremes(style)
                matches, bases_ignored = kit.misc.match_mI_variants(
                    style,
                    adjustment_extremes,
                )
                output_mI_variant_matches(style, matches, bases_ignored)

    def get_adjustment_extremes(self, style):
        try:
            light, bold = self.project.adjustment_for_matching_mI_variants
        except AttributeError:
            return None
        else:
            light_min, light_max = light
            bold_min, bold_max = bold
            axis_start = self.project.family.masters[0].weight_location
            axis_end = self.project.family.masters[-1].weight_location
            axis_range = axis_end - axis_start
            if axis_range == 0:
                ratio = 1
            else:
                ratio = (style.weight_location - axis_start) / axis_range
            return (
                light_min + (bold_min - light_min) * ratio,
                light_max + (bold_max - light_max) * ratio,
            )


    def generate_weight_class(self, style):
        with open(os.path.join(style.directory, 'WeightClass.fea'), 'w') as f:
            f.write('WeightClass {};\n'.format(str(style.weight_class)))

    def generate_references(self, style):
        with open(os.path.join(style.directory, 'features'), 'w') as f:
            lines = ['table head { FontRevision 1.000; } head;']
            for filename in [
                'classes',
                'classes_suffixing',
                'tables',
                'languagesystems',
                'GSUB_prefixing',
                'GSUB_lookups',
                'GSUB',
            ]:
                path = os.path.join(self.directory, filename + '.fea')
                if os.path.exists(path):
                    lines.append('include ({});'.format(os.path.relpath(path, style.directory)))
            if os.path.exists(os.path.join(style.directory, WriteFeaturesKernFDK.kKernFeatureFileName)):
                if self.project.family.script.is_indic:
                    kerning_feature_name = 'dist'
                else:
                    kerning_feature_name = 'kern'
                lines.append(
                    'feature {0} {{ include ({1}); }} {0};'.format(
                        kerning_feature_name,
                        WriteFeaturesKernFDK.kKernFeatureFileName,
                    )
                )
            if os.path.exists(os.path.join(style.directory, WriteFeaturesMarkFDK.kMarkClassesFileName)):
                lines.append('include ({});'.format(WriteFeaturesMarkFDK.kMarkClassesFileName))
            for feature_name, filename in [
                ('mark', WriteFeaturesMarkFDK.kMarkFeatureFileName),
                ('mkmk', WriteFeaturesMarkFDK.kMkmkFeatureFileName),
                ('abvm', WriteFeaturesMarkFDK.kAbvmFeatureFileName),
                ('blwm', WriteFeaturesMarkFDK.kBlwmFeatureFileName),
            ]:
                if os.path.exists(os.path.join(style.directory, filename)):
                    lines.append('feature {0} {{ include ({1}); }} {0};'.format(feature_name, filename))
            f.writelines(i + '\n' for i in lines)

# misc

ALIVE_CONSONANTS = [i + 'A' for i in kit.constants.CONSONANT_STEMS] + \
                   'GAbar JAbar DDAbar BAbar ZHA YAheavy DDAmarwari'.split()
DEAD_CONSONANTS = kit.constants.CONSONANT_STEMS

# font.groups['BASES_ALIVE']
# font.groups['BASES_DEAD']

consonant_name_sequences = [
    'K KA',
    'G GA',
]
base_name_sequences = [
    'K_KA',
    'G GA',
]

def match_mI():
    pass
def position_marks():
    pass

def match_mI_variants(style, adjustment_extremes):

    font = style.open()

    # get abvm_right_margin

    abvm_position_in_mE = get_abvm_position(
        font[style.family.script.abbreviation + 'mE'],
        in_base = False,
    )
    if abvm_position_in_mE is None:
        raise SystemExit("[WARNING] Can't find the abvm anchor in glyph `mE`!")
    else:
        abvm_right_margin = abs(abvm_position_in_mE)

    # get tolerance

    tolerance = get_stem_position(
        font[style.family.script.abbreviation + 'VA']
    ) * 0.5

    # prepare bases and matches

    bases = [
        Base(
            name_sequence = base_name_sequence,
            abvm_right_margin = abvm_right_margin,
        )
        for base_name_sequence in base_name_sequences
    ]
    if adjustment_extremes:
        targets = [base.target for base in bases]
        target_min = min(targets)
        target_max = max(targets)
        for target in targets:
            print('Old:', target, end=', ')
            ratio = (target - target_min) / (target_max - target_min)
            adjustment = (
                adjustment_extremes[0] +
                (adjustment_extremes[-1] - adjustment_extremes[0]) * ratio
            )
            target += adjustment
            print('New:', target, end='; ')
        print()

    matches = [
        Match(font=font, mI_variant_name=name)
        for name in font.groups['MATRA_I_ALTS']
    ]
    bases_ignored = []

    for base in bases:
        if base.target <= matches[0].overhanging:
            match = matches[0]
        elif base.target < matches[-1].overhanging:
            i = 0
            while matches[i].overhanging < base.target:
                candidate_short = matches[i]
                i += 1
            candidate_enough = matches[i]
            if (
                abs(candidate_enough.overhanging - base.target) <
                abs(candidate_short.overhanging - base.target)
            ):
                match = candidate_enough
            else:
                match = candidate_short
        elif base.target <= matches[-1].overhanging + tolerance:
            match = matches[-1]
        else:
            match = bases_ignored
        match.bases.append(base)

    return matches, bases_ignored

mI_NAME_STEM = 'mI.'
mI_ANCHOR_NAME = 'abvm.i'

def output_mI_variant_matches(style, matches, bases_ignored):

    lookup_name = 'matra_i_matching'
    do_position_marks = style.family.project.options[
        'position_marks_for_mI_variants'
    ]
    abvm_backup_path = os.path.join(
        style.directory,
        'backup--' + WriteFeaturesMarkFDK.kAbvmFeatureFileName,
    )
    abvm_path = os.path.join(
        style.directory,
        WriteFeaturesMarkFDK.kAbvmFeatureFileName,
    )
    matches_path = os.path.join(
        style.directory,
        lookup_name + '.fea',
    )
    def apply_mark_positioning_offset(value):
        return str(int(value) - matches[0].mI_variant.width)

    if do_position_marks:

        if os.path.exists(abvm_path_backup):
            kit.copy(abvm_backup_path, abvm_path)
        else:
            kit.copy(abvm_path, abvm_backup_path)
        with open(abvm_path, 'r') as f:
            abvm_content = f.read()

        abvm_lookup = re.search(
            r'''
                (?mx)
                lookup \s (MARK_BASE_%s) \s \{ \n
                ( .+ \n )+
                \} \s \1 ; \n
            ''' % mI_ANCHOR_NAME,
            abvm_content,
        ).group(0)
        print('abvm_lookup:', abvm_lookup)

        abvm_lookup_modified = abvm_lookup.replace(
            'pos base {}{}'.format(
                style.family.script.abbreviation,
                mI_NAME_STEM,
            ),
            'pos base @MATRA_I_BASES_',
        )

    class_def_lines = []
    class_def_lines.extend(
        kit.Feature.compose_glyph_class_def_lines(
            'MATRA_I_BASES_TOO_LONG',
            [base.name for base in bases_ignored]
        )
    )

    substitute_rule_lines = []
    substitute_rule_lines.append('lookup %s {' % lookup_name)
    for match in matches:
        if match.bases:
            if do_position_marks:
                abvm_lookup_modified = re.sub(
                    r'(?<=@MATRA_I_BASES_{} <anchor )-?\d+'.format(
                        match.number,
                    ),
                    apply_mark_positioning_offset,
                    abvm_lookup_modified,
                )
        else:
            print('\t\t`{}` is not used.'.format(match.name))
            if do_position_marks:
                abvm_lookup_modified = abvm_lookup_modified.replace(
                    '\tpos base @MATRA_I_BASES_' + match.number,
                    '\t# pos base @MATRA_I_BASES_' + match.number
                )
        class_def_lines.extend(
            kit.Feature.compose_glyph_class_def_lines(
                'MATRA_I_BASES_' + match.number,
                match.bases,
            )
        )
        substitute_rule_lines.append(
            "  {}sub {}mI' @MATRA_I_BASES_{} by {};".format(
                '' if match.bases else '# ',
                style.family.script.abbreviation,
                match.number,
                match.name,
            )
        )
    substitute_rule_lines.append('} %s;' % lookup_name)

    if do_position_marks:
        abvm_content_modified = abvm_content.replace(
            abvm_lookup,
            abvm_lookup_modified,
        )
        with open(abvm_path, 'w') as f:
            f.write(abvm_content_modified)

    with open(matches_path, 'w') as f:
        f.write(
            line + '\n'
            for line in class_def_lines + substitute_rule_lines
        )

class Base(object):
    def __init__(self, name_sequence, abvm_right_margin):
        self.name_sequence = name_sequence
        self.target = 0
        for glyph in base:
            if is_alive(glyph):
                self.target += get_stem_position(glyph, abvm_right_margin)
            else:
                self.target += glyph.width

class Match(object):
    def __init__(self, font, mI_variant_name):
        self.name = mI_variant_name
        self.mI_variant = font[self.name]
        self.number = self.mI_variant.name.partition('.')[2]
        self.overhanging = abs(self.mI_variant.rightMargin)
        self.bases = []

ABVM_ANCHOR_NAMES = ['abvm.e', 'abvm']
def get_abvm_position(glyph, in_base=True):
    anchor_name_prefix = '' if in_base else '_'
    for potential_anchor_name in ABVM_ANCHOR_NAMES:
        for anchor in glyph.anchors:
            if anchor.name == anchor_name_prefix + potential_anchor_name:
                return anchor.x

def get_stem_position(glyph, abvm_right_margin):
    abvm_position = get_abvm_position(glyph)
    if abvm_position is None:
        return glyph.width - abvm_right_margin
    else:
        return abvm_position
