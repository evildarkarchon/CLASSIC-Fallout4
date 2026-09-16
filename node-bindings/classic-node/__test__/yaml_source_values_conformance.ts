import * as classic from "../index.js";

/** Read generic source paths, names and enum distinctions from public exports. */
export function observeYamlSources(fixture: any): Record<string, unknown> {
    const variants: Record<string, classic.JsYamlSource> = {
        MAIN: classic.JsYamlSource.Main,
        IGNORE: classic.JsYamlSource.Ignore,
        GAME: classic.JsYamlSource.Game,
        GAME_LOCAL: classic.JsYamlSource.GameLocal,
        TEST: classic.JsYamlSource.Test
    };
    const sources = fixture.sources.map((name: string) => {
        if (!(name in variants)) throw new Error("unsupported source variant");
        return variants[name];
    });
    return {
        sources: sources.map((source: classic.JsYamlSource, index: number) => ({
            id: fixture.sources[index],
            path: classic.getYamlSourcePath(source, fixture.game).replaceAll("\\", "/"),
            name: classic.getYamlSourceDisplayName(source),
            gameName: classic.getYamlSourceDisplayNameWithGame(source, fixture.game)
        })),
        equal: sources[0] === classic.JsYamlSource.Main,
        different: sources[0] !== sources[1],
        distinct: new Set(sources).size
    };
}
