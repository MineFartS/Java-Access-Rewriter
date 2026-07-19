from tree_sitter import Language, Parser
import tree_sitter_kotlin

KOTLIN = Language(tree_sitter_kotlin.language())

TARGET_NODE_TYPES = {
    'class_declaration',
    'interface_declaration',
    'object_declaration',
    'function_declaration',
    'property_declaration'
}

# Real code-execution blocks where everything inside is strictly local
LOCAL_FUNCTION_SCOPES = {
    'function_declaration',
    'lambda_literal',
    'anonymous_initializer',
    'getter',
    'setter'
}

def is_inside_local_scope(node) -> bool:
    """Walks up the parent chain to see if the element is inside a functional execution block."""
    parent = node.parent
    while parent is not None:
        if parent.type in LOCAL_FUNCTION_SCOPES:
            return True
        parent = parent.parent
    return False

def is_top_level_property(node) -> bool:
    """Checks if a val/var is a global file-level variable (outside all classes/objects)."""
    if node.type != 'property_declaration':
        return False
        
    # Walk up the parent tree. If we cross a class/object before the file root, 
    # it's a class member variable (which we WANT to process). 
    # If we hit nothing but raw containers, it's a global package constant (skip it).
    parent = node.parent
    while parent is not None:
        if parent.type in {'class_declaration', 'interface_declaration', 'object_declaration', 'function_declaration'}:
            return False
        parent = parent.parent
    return True

def has_anonymous_type_or_value(node, content: str) -> bool:
    """Detects if a property declaration references or assigns an anonymous listener object."""
    node_text = content[node.start_byte:node.end_byte]
    return 'object :' in node_text or 'object:' in node_text

def collect_modifier_leaves(mod_node, content: str, results: list) -> None:
    """Recursively extracts precise leaf tokens inside a modifier block."""
    if len(mod_node.children) == 0:
        token_text = content[mod_node.start_byte:mod_node.end_byte]
        results.append((mod_node, token_text))
    else:
        for child in mod_node.children:
            collect_modifier_leaves(child, content, results)

def walk_tree(
    node, 
    content: str,
    modifications: list
) -> None:
    
    if node.type in TARGET_NODE_TYPES:
        # Rules for processing:
        # 1. Elements must not live inside localized function execution bodies
        # 2. Skip global file variables (like package-level ITEM_DELIM strings) to prevent namespace collision errors
        # 3. Skip declarations binding directly to local anonymous object types
        if not is_inside_local_scope(node) and not is_top_level_property(node) and not has_anonymous_type_or_value(node, content):
            
            # Find the modifiers structural child block cleanly by scanning types
            modifiers_node = None
            for child in node.children:
                if 'modifiers' in child.type:
                    modifiers_node = child
                    break
            
            has_override = False
            has_visibility = False
            visibility_tokens = []

            if modifiers_node:
                modifier_leaves = []
                collect_modifier_leaves(modifiers_node, content, modifier_leaves)
                
                for token_node, token_text in modifier_leaves:
                    if token_text == 'override':
                        has_override = True
                    elif token_text in {'private', 'protected', 'internal', 'public'}:
                        has_visibility = True
                        if token_text != 'public':
                            visibility_tokens.append(token_node)

            # Overrides retain base definition visibility rules; do not alter them
            if not has_override:
                if has_visibility:
                    # Replace private/internal with public directly at its byte position
                    for token in visibility_tokens:
                        modifications.append((token.start_byte, token.end_byte, "public"))
                else:
                    # No visibility keyword exists. Prepends 'public ' before structural keyword tokens.
                    target_insertion_point = node.start_byte
                    for child in node.children:
                        if child.type not in {'user_type', 'annotation', 'type_modifiers'}:
                            target_insertion_point = child.start_byte
                            break
                    
                    modifications.append((target_insertion_point, target_insertion_point, "public "))

    for child in node.children:
        walk_tree(child, content, modifications)


def rewrite(content: str) -> str:
    tree = Parser(KOTLIN).parse(content.encode('utf-8'))
    modifications = []

    walk_tree(tree.root_node, content, modifications)

    # De-duplicate to protect against any index index collisions
    unique_mods = {}
    for start, end, text in modifications:
        if (start, end) not in unique_mods:
            unique_mods[(start, end)] = text

    # Sort modifications from end of file to start of file to keep slice coordinates true
    sorted_mods = sorted(
        [(span[0], span[1], text) for span, text in unique_mods.items()],
        key=lambda x: x[0],
        reverse=True
    )

    # Patch the content via standard byte modification index mappings
    content_bytes = bytearray(content, "utf8")
    for start, end, replacement in sorted_mods:
        content_bytes[start:end] = bytes(replacement, "utf8")

    return content_bytes.decode("utf8")
