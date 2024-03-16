const JSON_PATH_PREFIX = "json-path";

// traverse the json content and add tags to identify keys and highlight values
const traverseJSON = (json, parent, path = JSON_PATH_PREFIX) => {
    const numChildren = Object.keys(json).length;
    const parentType = Array.isArray(json) ? "array" : "object";

    // iterate over the children
    Object.entries(json).forEach(([key, value], childIndex) => {
        let child = document.createElement("div");
        let childPath;
        let childType = typeof value;
        let childValue = childType === "string" ? `"${value}"` : value;

        // json path handling
        if (parentType === "array") {
            childPath = `${path}-item`;
        } else {
            childPath = `${path}-${key.replaceAll("_", "-")}`;
        }

        // key handling (unless within an array)
        if (parentType !== "array")
            child.innerHTML += `<span class="key">"${key}"</span>: `;

        // value handling (nested vs. non-nested datatype)
        if (!!value && childType === "object") {
            childType = Array.isArray(value) ? "array" : "object";
            child.innerHTML += childType === "array" ? "[" : "{";
            traverseJSON(value, child, childPath);
            child.innerHTML += childType === "array" ? "]" : "}";
        } else {
            childType = childType === "object" ? "null" : childType;
            child.innerHTML += `<span class="value ${childType}">${childValue}</span>`;
        }

        // comma handling (unless this is the last child)
        child.innerHTML += childIndex < numChildren - 1 ? "," : "";

        // identify a key by its full path
        child.classList.add(childPath);

        parent.appendChild(child);
    });
}

// list duplicated keys
const listDuplicatedKeys = (
    json, path, visitedKeys = [], visitedPaths = [], duplicatedKeys = []
) => {
    const parentType = Array.isArray(json) ? "array" : "object";

    // iterate over the children
    Object.entries(json).forEach(([key, value]) => {
        const childPath = parentType === "array" ? `${path}-item` : `${path}-${key}`;

        // json path handling (skip the rest of the loop if already visited)
        if (!visitedPaths.includes(childPath)) {
            visitedPaths.push(childPath);
        } else {
            return
        }

        // duplication check
        if (parentType !== "array") {
            if (visitedKeys.includes(key) && !duplicatedKeys.includes(key))
                duplicatedKeys.push(key);
            visitedKeys.push(key);
        }

        // value handling (nested vs. non-nested datatype)
        if (!!value && typeof value === "object")
            duplicatedKeys = listDuplicatedKeys(
                value, childPath, visitedKeys, visitedPaths, duplicatedKeys
            );
    });

    return duplicatedKeys;
}

// guess polars type
const guessPolarsType = (value, type) => {
    let polarsType = "Unknown";

    if (type === "boolean") {
        polarsType = "Boolean";
    } else if (type === "null") {
        polarsType = "Null";
    } else if (type === "number") {
        polarsType = Number.isInteger(value) ? "Int64" : "Float64";
    } else if (type === "string") {
        polarsType = "String";
    }

    return polarsType;
}

// traverse the json content and generate the corresponding schema entries
const generateSchema = (
    json, parent, path = JSON_PATH_PREFIX, visited = [], duplicated = []
) => {
    const parentType = Array.isArray(json) ? "array" : "object";
    const lambda = s => s.substring(10).replaceAll("-item", "").replaceAll("-", "_");

    // iterate over the children
    Object.entries(json).forEach(([key, value]) => {
        let child = document.createElement("div");
        let childPath;
        let childType = typeof value;
        let polarsType;
        let renamedKey;

        // json path handling
        if (parentType === "array") {
            childPath = `${path}-item`;
            renamedKey = lambda(path);
        } else {
            childPath = `${path}-${key.replaceAll("_", "-")}`;
            renamedKey = lambda(childPath);
        }

        // json path handling (skip the rest of the loop if already visited)
        if (!visited.includes(childPath)) {
            visited.push(childPath);
        } else {
            return
        }

        // key handling (unless within an array)
        if (parentType !== "array") {
            child.innerHTML += `<span class="key">${key}</span>`;
            if (duplicated.includes(key) && renamedKey !== key) {
                child.innerHTML += `=<span class="renamed-key">${renamedKey}</span>: `;
            } else {
                child.innerHTML += `: `;
            }
        }

        // value handling (nested vs. non-nested datatype)
        if (!!value && childType === "object") {
            childType = Array.isArray(value) ? "array" : "object";
            child.innerHTML += childType === "array" ? "List(" : "Struct(";
            generateSchema(value, child, childPath, visited, duplicated);
            child.innerHTML += ")";
        } else {
            childType = childType === "object" ? "null" : childType;
            polarsType = guessPolarsType(value, childType);
            child.innerHTML += `<span class="value ${childType}">${polarsType}</span>`;
        }

        // identify a key by its full path
        child.classList.add(childPath);

        parent.appendChild(child);
    });
}

// parse the source json
const highlightSource = (json, parent) => {
    if (!!json && typeof json === "object") {
        parent.innerHTML += Array.isArray(json) ? "[" : "{";
        traverseJSON(json, parent);
        parent.innerHTML += Array.isArray(json) ? "]" : "}";
    } else {
        traverseJSON(json, parent);
    }
}

// react to hovering on either side
const addEventListeners = (object, otherObject) => {
    object.querySelectorAll("div").forEach(element => {

        // highlight the element and scroll it into view (if not visible)
        element.addEventListener("mouseenter", (event) => {
            const className = `.${event.target.classList[0]}`;
            document.querySelectorAll(className).forEach(div => {
                div.classList.add("highlighted");
            });
            otherObject.querySelectorAll(className)[0].scrollIntoView({
                block: "nearest", inline: "center"
            });
        });

        // remove the highlight
        element.addEventListener("mouseleave", (event) => {
            document.querySelectorAll(`.${event.target.classList[0]}`).forEach(div => {
                div.classList.remove("highlighted");
            });
        });

    });
}

// add to the page
document.querySelector("#unpack").innerHTML += `
<textarea
  id="unpack-json-input"
  placeholder="paste/edit your JSON content here"
  rows="3">
</textarea>
<div class="unpacked">
  <div id="unpack-parsed-input"></div>
  <div id="unpack-rough-schema"></div>
</div>
`;

// relevant object
const input = document.querySelector("#unpack-json-input")

const parsedInput = document.querySelector("#unpack-parsed-input");
const roughSchema = document.querySelector("#unpack-rough-schema");

// run the routine
const process = (json) => {
    input.classList.remove("error");
    parsedInput.innerHTML = "";
    roughSchema.innerHTML = "";
    highlightSource(json, parsedInput);
    generateSchema(json, roughSchema, JSON_PATH_PREFIX, [],  listDuplicatedKeys(json));
    addEventListeners(parsedInput, roughSchema);
    addEventListeners(roughSchema, parsedInput);
}

// react to change of the input textarea
input.addEventListener("keyup", (event) => {
    try {
        const json = JSON.parse(input.value);
        process(json);
        window.scrollTo(0, window.innerHeight);
    } catch(e) {
        input.classList.add("error");
    }
});

// enough documentation?
process({
    simple_float: 1.23,
    nested_struct: {
        simple_boolean: false,
        string: "foo",
        null: null,
        list_in_struct: {floats: [1.23e1, 4.56e4, 7.89e7]},
        integers: [1, 2, 3],
    },
    list_of_structs: [
        {integer: 1, string: "3", boolean: true},
        {integer: 2, string: "4", boolean: false},
    ],
    string: "bar"
});
