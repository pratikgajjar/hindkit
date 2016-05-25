#!/usr/bin/env AFDKOPython
# encoding: UTF-8
from __future__ import division, absolute_import, print_function, unicode_literals

import os, collections
import WriteFeaturesKernFDK, WriteFeaturesMarkFDK
import hindkit as kit

class BaseFeature(kit.BaseFile):

    def __init__(self, project, name, style, filename_group):
        if style:
            abstract_directory = style.abstract_directory
        else:
            abstract_directory = kit.Project.directories["features"]
        super(BaseFeature, self).__init__(
            name,
            file_format = "FEA",
            project = project,
            filename_group = filename_group,
            abstract_directory = abstract_directory,
        )
        self.style = style

    @staticmethod
    def sort_names(names, order):
        return (
            [i for i in order if i in names] +
            [i for i in names if i not in order]
        )

    @staticmethod
    def compose_glyph_class_def_lines(class_name, glyph_names):
        if glyph_names:
            glyph_class_def_lines = (
                ["@{} = [".format(class_name)] +
                ["  {}".format(glyph_name) for glyph_name in glyph_names] +
                ["];", ""]
            )
        else:
            glyph_class_def_lines = ["# @{} = [];".format(class_name), ""]
        return glyph_class_def_lines


class FeatureClasses(BaseFeature):

    def generate(self):

        lines = []

        if self.project.options["prepare_mark_positioning"]:

            glyph_classes = []
            glyph_classes.extend([(WriteFeaturesMarkFDK.kCombMarksClassName, kit.filters.marks)])

            if self.project.options["match_mI_variants"]:
                glyph_classes.extend([
                    (FeatureMatches.CLASS_NAME_mI_VARIANTS, kit.filters.mI_variants),
                    (FeatureMatches.CLASS_NAME_BASES_ALIVE, kit.filters.bases_alive),
                    (FeatureMatches.CLASS_NAME_BASES_DEAD, kit.filters.bases_dead),
                    (FeatureMatches.CLASS_NAME_BASES_FOR_LONG_mI, kit.filters.bases_for_long_mII),
                ])

            font_0 = self.project.products[0].style.open()

            glyph_order = self.project.glyph_data.glyph_order
            for class_name, filter_function in glyph_classes:
                glyph_names = [
                    glyph.name for glyph in filter(
                        lambda glyph: filter_function(self.project.family, glyph),
                        font_0,
                    )
                ]
                glyph_names = self.sort_names(glyph_names, glyph_order)
                font_0.groups.update({class_name: glyph_names})
                lines.extend(
                    self.compose_glyph_class_def_lines(class_name, glyph_names)
                )
            font_0.save()

            for style in (i.style for i in self.project.products[1:]):
                font = style.open()
                font.groups.update(font_0.groups)
                font.save()

        if lines:
            with open(self.path, "w") as f:
                f.writelines(i + "\n" for i in lines)


class FeatureTables(BaseFeature):

    def generate(self):

        info = self.project.family.info
        client = self.project.family.client

        lines = []
        tables = collections.OrderedDict([
            ("hhea", []),
            ("OS/2", []),
            ("GDEF", []),
            ("name", []),
        ])

        tables["OS/2"].extend([
            "include (WeightClass.fea);",
            "fsType {};".format(client.tables["OS/2"]["fsType"]),
            "Vendor \"{}\";".format(client.tables["OS/2"]["Vendor"]),
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

            if client.vertical_metrics_strategy == "Google Fonts":
                if info.openTypeOS2TypoAscender is None:
                    info.openTypeOS2TypoAscender = info.openTypeHheaAscender
                if info.openTypeOS2TypoDescender is None:
                    info.openTypeOS2TypoDescender = info.openTypeHheaDescender
                if info.openTypeOS2TypoLineGap is None:
                    info.openTypeOS2TypoLineGap = info.openTypeHheaLineGap
            elif client.vertical_metrics_strategy == "ITF":
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

            tables["hhea"].extend([
                "Ascender {};".format(info.openTypeHheaAscender),
                "Descender {};".format(info.openTypeHheaDescender),
                "LineGap {};".format(info.openTypeHheaLineGap),
            ])
            tables["OS/2"].extend([
                "TypoAscender {};".format(info.openTypeOS2TypoAscender),
                "TypoDescender {};".format(info.openTypeOS2TypoDescender),
                "TypoLineGap {};".format(info.openTypeOS2TypoLineGap),
                "winAscent {};".format(info.openTypeOS2WinAscent),
                "winDescent {};".format(info.openTypeOS2WinDescent),
            ])

        # tables["OS/2"].extend(self.project.generate_UnicodeRange)
        # tables["OS/2"].extend(self.project.generate_CodePageRange)

        if self.project.options["override_GDEF"]:
            GDEF_records = {
                "bases": "",
                "ligatures": "",
                "marks": "",
                "components": "",
            }
            if self.project.options["prepare_mark_positioning"] or os.path.exists(os.path.join(self.directory, "classes.fea")):
                GDEF_records["marks"] = "@{}".format(WriteFeaturesMarkFDK.kCombMarksClassName)
            if os.path.exists(os.path.join(self.directory, "classes_suffixing.fea")):
                GDEF_records["marks"] = "@{}".format("COMBINING_MARKS_GDEF")
            tables["GDEF"].extend([
                "GlyphClassDef {bases}, {ligatures}, {marks}, {components};".format(**GDEF_records)
            ])

        tables["name"].extend(
            "nameid {} \"{}\";".format(
                name_id,
                content.encode("unicode_escape").replace("\\x", "\\00").replace("\\u", "\\")
            )
            for name_id, content in sorted(client.tables["name"].items())
            if content
        )

        for name, entries in tables.items():
            if entries:
                lines.append("table %s {" % name)
                lines.extend("  " + i for i in entries)
                lines.append("} %s;" % name)

        if lines:
            with open(self.path, "w") as f:
                f.writelines(i + "\n" for i in lines)


class FeatureLanguagesystems(BaseFeature):
    def generate(self):
        lines = ["languagesystem DFLT dflt;"]
        for tag in self.project.family.script.tags:
            lines.append("languagesystem {} dflt;".format(tag))
        if lines:
            with open(self.path, "w") as f:
                f.writelines(i + "\n" for i in lines)


class FeatureMark(BaseFeature):
    def generate(self):
        WriteFeaturesMarkFDK.kMarkFeatureFileName = self.filename_with_extension
        WriteFeaturesMarkFDK.MarkDataClass(
            font = self.style.open(),
            folderPath = self.style.directory,
            trimCasingTags = False,
            genMkmkFeature = self.project.options["prepare_mark_to_mark_positioning"],
            writeClassesFile = True,
            indianScriptsFormat = self.project.family.script.is_indic,
        )


class FeatureKern(BaseFeature):
    def generate(self):
        WriteFeaturesKernFDK.kKernFeatureFileName = self.filename_with_extension
        WriteFeaturesKernFDK.KernDataClass(
            font = self.style.open(),
            folderPath = self.style.directory,
        )
        try:
            self.project.postprocess_kerning
        except AttributeError:
            pass
        else:
            kern_path = self.path
            if os.path.exists(kern_path):
                with open(kern_path) as f:
                    content = f.read()
                with open(kern_path, "w") as f:
                    f.write(self.project.postprocess_kerning(content))


class FeatureWeightClass(BaseFeature):
    def generate(self):
        with open(self.path, "w") as f:
            f.write("WeightClass {};\n".format(str(self.style.weight_class)))


class FeatureMatches(BaseFeature):

    class Base(object):
        def __init__(self, feature, name_sequence):
            self.name_sequence = name_sequence
            self.glyphs = [feature.font[name] for name in self.name_sequence.split()]
            self.target = None
            for glyph in reversed([
                g for g in self.glyphs
                if g.name[2:] not in ["Virama", "Nukta", "RAc2"]
            ]):
                if self.target is None:
                    self.target = feature._get_stem_position(glyph)
                else:
                    self.target += glyph.width

    class Match(object):
        def __init__(self, feature, mI_variant_name):
            self.name = mI_variant_name
            if self.name:
                self.mI_variant = feature.font[self.name]
                self.number = self.mI_variant.name.partition(".")[2]
                self.overhanging = abs(self.mI_variant.rightMargin)
            self.bases = []

    # POTENTIAL_MODES = [
    #     "single glyph", "glyph sequence",
    #     "position marks", "ligate marks",
    # ]

    CLASS_NAME_mI_VARIANTS = "mI_VARIANTS"
    CLASS_NAME_BASES_ALIVE = "BASES_ALIVE"
    CLASS_NAME_BASES_DEAD = "BASES_DEAD"
    CLASS_NAME_BASES_FOR_LONG_mI = "BASES_FOR_LONG_mI"

    CONSONANTS_ALIVE = [
        i + "A" for i in kit.constants.CONSONANT_STEMS
    ] + "GAbar JAbar DDAbar BAbar ZHA YAheavy DDAmarwari".split()
    CONSONANTS_DEAD = kit.constants.CONSONANT_STEMS

    mI_NAME_STEM = "mI"

    def generate(self):

        self.font = self.style.open()

        mI_variant_names = self.font.groups[self.CLASS_NAME_mI_VARIANTS]
        if mI_variant_names:
            self.matches = [self.Match(self, name) for name in mI_variant_names]
        else:
            return

        self.not_matched = self.Match(self, None)

        abvm_position_in_mE = self._get_abvm_position(
            self.font[self.style.family.script.abbr + "mE"],
            in_base = False,
        )
        if abvm_position_in_mE is None:
            raise SystemExit("[WARNING] Can't find the abvm anchor in glyph `mE`!")
        else:
            self.abvm_right_margin = abs(abvm_position_in_mE)

        self.bases = [
            self.Base(self, name_sequence)
            for name_sequence in self._get_base_name_sequences()
        ]

        self.adjustment_extremes = self._get_adjustment_extremes()
        if self.adjustment_extremes:
            targets = [base.target for base in self.bases]
            target_min = min(targets)
            target_max = max(targets)
            for i, target in enumerate(targets):
                print("Old:", target, end=", ")
                ratio = (target - target_min) / (target_max - target_min)
                ae = self.adjustment_extremes
                adjustment = ae[0] + (ae[-1] - ae[0]) * ratio
                targets[i] += adjustment
                print("New:", targets[i], end="; ")
            print()

        self.tolerance = self._get_stem_position(
            self.font[self.style.family.script.abbr + "VA"]
        ) * 0.5

        for base in self.bases:
            match = self.match_mI_variants(base)
            match.bases.append(base)

        self.name_default = self.style.family.script.abbr + self.mI_NAME_STEM

        self.substitute_rule_lines = []
        for match in self.matches:
            self.output_mI_variant_matches(match)
        with open(self.path, "w") as f:
            f.writelines([
                "lookup %s {\n" % self.name,
                # "  lookupflag IgnoreMarks;\n",
            ])
            f.writelines("  " + l + "\n" for l in self.substitute_rule_lines)
            f.writelines([
                # "  lookupflag 0;\n",
                "} %s;\n" % self.name,
            ])

        if self.project.options["position_marks_for_mI_variants"] and \
        self.project.options["match_mI_variants"] != "sequence":
            self.output_mark_positioning_for_mI_variants()

    def _get_adjustment_extremes(self):
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
                ratio = (self.style.weight_location - axis_start) / axis_range
            return (
                light_min + (bold_min - light_min) * ratio,
                light_max + (bold_max - light_max) * ratio,
            )

    def _get_abvm_position(self, glyph, in_base=True):
        anchor_name_prefix = "" if in_base else "_"
        for potential_anchor_name in ["abvm.candra", "abvm.e", "abvm"]:
            for anchor in glyph.anchors:
                if anchor.name == anchor_name_prefix + potential_anchor_name:
                    return anchor.x

    def _get_stem_position(self, glyph):
        abvm_position = self._get_abvm_position(glyph)
        if abvm_position is None:
            return glyph.width - self.abvm_right_margin
        else:
            return abvm_position

    base_names_alive = None
    base_names_dead = None

    def _get_base_name_sequences(self):
        if self.base_names_alive is None:
            self.base_names_alive = self.font.groups[self.CLASS_NAME_BASES_ALIVE]
        for alive in self.base_names_alive:
            if alive in self.font:
                yield alive
        if self.project.options["match_mI_variants"] == "sequence":
            if self.base_names_dead is None:
                self.base_names_dead = self.font.groups[self.CLASS_NAME_BASES_DEAD]
            for dead in self.base_names_dead:
                for alive in self.base_names_alive:
                    yield dead + " " + alive

    def match_mI_variants(self, base):
        if base.target <= self.matches[0].overhanging:
            return self.matches[0]
        elif base.target < self.matches[-1].overhanging:
            i = 0
            while self.matches[i].overhanging < base.target:
                candidate_short = self.matches[i]
                i += 1
            candidate_enough = self.matches[i]
            if (
                abs(candidate_enough.overhanging - base.target) <
                abs(candidate_short.overhanging - base.target)
            ):
                return candidate_enough
            else:
                return candidate_short
        elif base.target <= self.matches[-1].overhanging + self.tolerance:
            return self.matches[-1]
        else:
            return self.not_matched

    def output_mI_variant_matches(self, match):

        if not match.bases:
            print("\t\t`{}` is not used.".format(match.name))
            return

        single_glyph_bases = []
        multiple_glyph_bases = []
        for base in match.bases:
            if len(base.glyphs) == 1:
                single_glyph_bases.append(base)
            else:
                multiple_glyph_bases.append(base)

        if single_glyph_bases:
            self.substitute_rule_lines.append(
                "sub {}' [{}] by {};".format(
                    self.name_default,
                    " ".join(base.glyphs[0].name for base in single_glyph_bases),
                    match.name,
                ),
            )
        for base in multiple_glyph_bases:
            self.substitute_rule_lines.append(
                "sub {}' {} by {};".format(self.name_default, base.name_sequence, match.name),
            )

    def _modify(matchobj):
        match = match_dict[matchobj.group(1)]
        modified = "pos base [{}] <anchor {}".format(
            " ".join(base.glyphs[0].name for base in match.bases),
            int(matchobj.group(2)) - self.font[self.name_default].width,
        )
        if not match.bases:
            modified = "# " + modified
        return modified

    def output_mark_positioning_for_mI_variants(self):

        abvm_backup_path = os.path.join(
            self.style.directory,
            "backup--" + WriteFeaturesMarkFDK.kAbvmFeatureFileName,
        )
        abvm_path = os.path.join(
            self.style.directory,
            WriteFeaturesMarkFDK.kAbvmFeatureFileName,
        )
        if os.path.exists(abvm_path_backup):
            kit.copy(abvm_backup_path, abvm_path)
        else:
            kit.copy(abvm_path, abvm_backup_path)

        pattern_begin = re.compile(r"lookup MARK_BASE_%s \{$" % self.mI_ANCHOR_NAME)
        pattern_end = re.compile(r"\} MARK_BASE_%s;$" % self.mI_ANCHOR_NAME)
        match_dict = {match.number: match for match in self.matches}
        with open(abvm_path, "r") as f:
            lines_modified = []
            is_inside_the_lookup = False
            for line in f:
                if is_inside_the_lookup:
                    if pattern_end.match(line):
                        is_inside_the_lookup = False
                        line_modified = line
                    else:
                        line_modified = re.sub(
                            r"pos base {}\.(\d\d) <anchor (-?\d+)".format(self.name_default),
                            self._modify,
                            line,
                        )
                else:
                    if pattern_begin.match(line):
                        is_inside_the_lookup = True
                        line_modified = line
                    else:
                        line_modified = line
                lines_modified.append(line_modified)

        with open(abvm_path, "w") as f:
            f.writelines(lines_modified)


class FeatureReferences(BaseFeature):
    def generate(self):
        with open(self.path, "w") as f:
            lines = ["table head { FontRevision 1.000; } head;"]
            for feature in [
                self.project.feature_classes,
                self.project.feature_tables,
                self.project.feature_languagesystems,
                self.project.feature_gsub,
            ]:
                for i in feature.file_group:
                    if os.path.exists(i.path):
                        lines.append(
                            "include ({});".format(
                                os.path.relpath(i.path, self.style.directory)
                            )
                        )
            if os.path.exists(self.project.feature_kern.path):
                lines.append(
                    "feature %(tag)s { include (%(path)s); } %(tag)s;" % {
                        "tag": "dist" if self.project.family.script.is_indic else "kern",
                        "path": os.path.relpath(self.project.feature_kern.path, self.style.directory),
                    }
                )
            if os.path.exists(os.path.join(self.style.directory, WriteFeaturesMarkFDK.kMarkClassesFileName)):
                lines.append("include ({});".format(WriteFeaturesMarkFDK.kMarkClassesFileName))
            for feature_name, filename in [
                ("mark", WriteFeaturesMarkFDK.kMarkFeatureFileName),
                ("mkmk", WriteFeaturesMarkFDK.kMkmkFeatureFileName),
                ("abvm", WriteFeaturesMarkFDK.kAbvmFeatureFileName),
                ("blwm", WriteFeaturesMarkFDK.kBlwmFeatureFileName),
            ]:
                if os.path.exists(os.path.join(self.style.directory, filename)):
                    lines.append(
                        "feature %(tag)s { include (%(path)s); } %(tag)s;" % {
                            "tag": feature_name,
                            "path": filename,
                        }
                    )
            f.writelines(i + "\n" for i in lines)


class Feature(object):
    NAME_TO_CLASS_MAP = {
        "classes": FeatureClasses,
        "tables": FeatureTables,
        "languagesystems": FeatureLanguagesystems,
        "kern": FeatureKern,
        "mark": FeatureMark,
        "mI_variant_matches": FeatureMatches,
        "WeightClass": FeatureWeightClass,
        "features": FeatureReferences,
    }
    def __new__(cls, project, name, style=None, filename_group=None):
        F = cls.NAME_TO_CLASS_MAP.get(name, BaseFeature)
        return F(project, name, style, filename_group)
